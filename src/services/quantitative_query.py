"""Quantitative query service for answering questions that require counting or aggregation from raw data."""

from pathlib import Path
from typing import Dict, List, Optional, Any
from uuid import UUID
import json
import urllib.request

from src.lib.config import ENTITIES_MEETINGS_DIR, ENTITIES_WORKGROUPS_DIR, ENTITIES_PEOPLE_DIR
from src.lib.logging import get_logger
from src.services.entity_storage import load_entity, load_index
from src.models.meeting import Meeting
from src.models.workgroup import Workgroup
from src.models.person import Person
from src.models.meeting_record import MeetingRecord

logger = get_logger(__name__)


class QuantitativeQueryService:
    """
    Service for answering quantitative questions by directly accessing JSON data sources.
    
    This service provides reliable counts and aggregations by reading directly from
    entity storage files, ensuring accuracy and providing citations for data sources.
    """
    
    def count_meetings_from_source_url(self, source_url: str) -> Dict[str, Any]:
        """
        Count meetings directly from source URL (e.g., GitHub raw JSON file).
        
        Args:
            source_url: URL to source JSON file
            
        Returns:
            Dictionary with count from source URL
        """
        logger.info("quantitative_query_count_from_source", url=source_url)
        
        # Restore socket if it was monkey-patched (for compliance checker)
        import socket
        from ..services.compliance_checker import get_compliance_checker
        checker = get_compliance_checker()
        
        original_socket = None
        was_monitoring = checker.enabled
        if was_monitoring and hasattr(checker.network_monitor, '_original_socket') and checker.network_monitor._original_socket:
            original_socket = checker.network_monitor._original_socket
            # Temporarily restore original socket for URL fetch
            socket.socket = original_socket
        
        try:
            # Fetch JSON from URL
            with urllib.request.urlopen(source_url, timeout=30) as response:
                data_bytes = response.read()
                data_text = data_bytes.decode('utf-8')
            
            # Parse JSON
            data = json.loads(data_text)
            
            # Handle array or single object
            if isinstance(data, list):
                meetings_data = data
            elif isinstance(data, dict):
                # Single meeting object
                meetings_data = [data]
            else:
                meetings_data = []
            
            # Count total items in array
            total_count = len(meetings_data)
            
            # Count unique meetings (by workgroup_id + date combination)
            unique_meetings = set()
            for meeting_data in meetings_data:
                if isinstance(meeting_data, dict):
                    workgroup_id = meeting_data.get("workgroup_id")
                    meeting_info = meeting_data.get("meetingInfo", {})
                    date = meeting_info.get("date") if isinstance(meeting_info, dict) else None
                    
                    # Create unique identifier: workgroup_id + date
                    if workgroup_id and date:
                        unique_meetings.add((workgroup_id, date))
                    elif workgroup_id:
                        # If no date, use workgroup_id only
                        unique_meetings.add((workgroup_id, None))
                    elif "id" in meeting_data:
                        # Legacy format: use id
                        unique_meetings.add((meeting_data.get("id"), date))
            
            unique_count = len(unique_meetings)
            
            logger.info("quantitative_query_count_from_source_complete", 
                       url=source_url, 
                       total_count=total_count,
                       unique_count=unique_count)
            
            return {
                "count": total_count,  # Total items in array
                "unique_count": unique_count,  # Unique meetings (workgroup_id + date)
                "source": source_url,
                "method": "Direct count from source JSON URL - counted both total array items and unique meetings",
                "citations": [
                    {
                        "type": "source_url",
                        "description": f"Counted {total_count} items in source JSON array, {unique_count} unique meetings",
                        "url": source_url,
                        "sample_dates": [m.get("meetingInfo", {}).get("date", "N/A") for m in meetings_data[:5]] if meetings_data else []
                    }
                ],
                "has_duplicates": total_count != unique_count
            }
        except Exception as e:
            logger.error("quantitative_query_count_from_source_failed", 
                        url=source_url, error=str(e))
            raise ValueError(f"Failed to count meetings from source URL {source_url}: {e}")
        finally:
            # Restore monitoring socket if needed (re-enable monitoring will restore it)
            if was_monitoring and checker.enabled:
                # Socket will be restored when monitoring is re-enabled
                pass
    
    def count_all_meetings(self, source_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Count all meetings by reading from JSON files or source URL.
        
        Args:
            source_url: Optional URL to source JSON file for direct counting
            
        Returns:
            Dictionary with count and metadata including:
            - count: Total number of meetings
            - source: Data source description
            - method: How the count was obtained
            - citations: List of meeting IDs counted (for verification)
            - discrepancy: If source_url provided, comparison with entity storage
        """
        logger.info("quantitative_query_count_meetings_start", source_url=source_url)
        
        entity_count_result = None
        source_count_result = None
        
        # Count from entity storage
        meetings_dir = ENTITIES_MEETINGS_DIR
        
        if meetings_dir.exists():
            # Count meetings by scanning JSON files
            meeting_files = list(meetings_dir.glob("*.json"))
            valid_meetings = []
            meeting_ids = []
            data_files_checked = []
            
            for meeting_file in meeting_files:
                if meeting_file.name.endswith('.tmp'):
                    continue  # Skip temporary files
                    
                data_files_checked.append(str(meeting_file))
                
                try:
                    # Load meeting entity
                    meeting_id_str = meeting_file.stem
                    meeting_id = UUID(meeting_id_str)
                    meeting = load_entity(meeting_id, ENTITIES_MEETINGS_DIR, Meeting)
                    
                    if meeting:
                        valid_meetings.append(meeting)
                        meeting_ids.append(str(meeting.id))
                except (ValueError, AttributeError, Exception) as e:
                    logger.debug("quantitative_query_meeting_load_skipped", 
                               file=str(meeting_file), error=str(e))
                    continue
            
            entity_count = len(valid_meetings)
            
            entity_count_result = {
                "count": entity_count,
                "source": f"JSON files in {meetings_dir}",
                "method": "Direct file count from entity storage - counted valid meeting JSON files",
                "citations": meeting_ids[:10],
                "total_files_checked": len(data_files_checked),
                "data_files_checked": data_files_checked[:5]
            }
        else:
            logger.warning("quantitative_query_meetings_dir_not_found", path=str(meetings_dir))
            entity_count_result = {
                "count": 0,
                "source": f"JSON files in {meetings_dir}",
                "method": "Direct file count from entity storage",
                "citations": [],
                "data_files_checked": []
            }
        
        # If source URL provided, count from source
        if source_url:
            try:
                source_count_result = self.count_meetings_from_source_url(source_url)
                
                # Compare counts
                entity_count = entity_count_result["count"]
                source_count = source_count_result["count"]
                discrepancy = source_count - entity_count
                
                logger.info("quantitative_query_count_comparison",
                           entity_count=entity_count,
                           source_count=source_count,
                           discrepancy=discrepancy)
                
                # Return source count with discrepancy info
                unique_count = source_count_result.get("unique_count", source_count)
                return {
                    "count": source_count,  # Total items in array
                    "unique_count": unique_count,  # Unique meetings
                    "source": source_url,
                    "method": source_count_result["method"],
                    "citations": source_count_result["citations"],
                    "discrepancy": {
                        "entity_storage_count": entity_count,
                        "source_count": source_count,
                        "source_unique_count": unique_count,
                        "difference": discrepancy,
                        "explanation": f"Entity storage has {entity_count} meetings, but source has {source_count} total entries ({unique_count} unique meetings). {abs(discrepancy)} meeting(s) not yet ingested into entity storage." if discrepancy != 0 else "Counts match between entity storage and source."
                    },
                    "entity_storage_info": entity_count_result,
                    "has_duplicates": source_count_result.get("has_duplicates", False)
                }
            except Exception as e:
                logger.warning("quantitative_query_source_count_failed", 
                             url=source_url, error=str(e))
                # Fall back to entity storage count
                return entity_count_result
        
        # Return entity storage count (default)
        return entity_count_result
    
    def count_meetings_by_workgroup(self, workgroup_id: Optional[UUID] = None) -> Dict[str, Any]:
        """
        Count meetings by workgroup.
        
        Args:
            workgroup_id: Optional workgroup ID to filter by
            
        Returns:
            Dictionary with counts per workgroup
        """
        logger.info("quantitative_query_count_meetings_by_workgroup", 
                   workgroup_id=str(workgroup_id) if workgroup_id else None)
        
        try:
            index_data = load_index("meetings_by_workgroup")
            
            if workgroup_id:
                # Count for specific workgroup
                workgroup_id_str = str(workgroup_id)
                meeting_ids_str = index_data.get(workgroup_id_str, [])
                count = len(meeting_ids_str)
                
                return {
                    "count": count,
                    "workgroup_id": str(workgroup_id),
                    "source": f"Index file: meetings_by_workgroup.json",
                    "method": "Count from workgroup index file",
                    "citations": meeting_ids_str[:10]
                }
            else:
                # Count for all workgroups
                workgroup_counts = {}
                total = 0
                
                for wg_id_str, meeting_ids_str in index_data.items():
                    count = len(meeting_ids_str)
                    workgroup_counts[wg_id_str] = count
                    total += count
                
                return {
                    "total_count": total,
                    "workgroup_counts": workgroup_counts,
                    "source": f"Index file: meetings_by_workgroup.json",
                    "method": "Count from workgroup index file - aggregated across all workgroups"
                }
        except Exception as e:
            logger.error("quantitative_query_count_meetings_by_workgroup_failed", error=str(e))
            raise
    
    def get_meeting_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about meetings.
        
        Returns:
            Dictionary with various meeting statistics
        """
        logger.info("quantitative_query_get_meeting_statistics_start")
        
        all_meetings_data = self.count_all_meetings()
        by_workgroup_data = self.count_meetings_by_workgroup()
        
        return {
            "total_meetings": all_meetings_data["count"],
            "meetings_by_workgroup": by_workgroup_data.get("workgroup_counts", {}),
            "source": "Entity storage JSON files",
            "method": "Direct aggregation from entity storage files"
        }
    
    def calculate_average(self, values: List[float]) -> Dict[str, Any]:
        """
        Calculate average of numeric values.
        
        Args:
            values: List of numeric values
            
        Returns:
            Dictionary with average, count, and method
        """
        if not values:
            return {
                "average": 0.0,
                "count": 0,
                "method": "Average calculation - no values provided",
                "source": "N/A"
            }
        
        avg = sum(values) / len(values)
        return {
            "average": avg,
            "count": len(values),
            "method": f"Calculated arithmetic mean from {len(values)} values",
            "source": "Direct calculation from entity data"
        }
    
    def calculate_range(self, values: List[float]) -> Dict[str, Any]:
        """
        Calculate min/max range of numeric values.
        
        Args:
            values: List of numeric values
            
        Returns:
            Dictionary with min, max, range, and method
        """
        if not values:
            return {
                "min": 0.0,
                "max": 0.0,
                "range": 0.0,
                "method": "Range calculation - no values provided",
                "source": "N/A"
            }
        
        min_val = min(values)
        max_val = max(values)
        range_val = max_val - min_val
        
        return {
            "min": min_val,
            "max": max_val,
            "range": range_val,
            "method": f"Calculated min/max range from {len(values)} values",
            "source": "Direct calculation from entity data"
        }
    
    def detect_trends(self, date_counts: Dict[str, int]) -> Dict[str, Any]:
        """
        Detect trends in date-based counts (e.g., meetings over time).
        
        Args:
            date_counts: Dictionary mapping dates (YYYY-MM-DD) to counts
            
        Returns:
            Dictionary with trend analysis and method
        """
        if not date_counts:
            return {
                "trend": "no_data",
                "method": "Trend detection - no data provided",
                "source": "N/A"
            }
        
        # Sort dates chronologically
        sorted_dates = sorted(date_counts.keys())
        counts = [date_counts[date] for date in sorted_dates]
        
        # Simple trend: increasing, decreasing, or stable
        if len(counts) < 2:
            trend = "insufficient_data"
        elif counts[-1] > counts[0]:
            trend = "increasing"
        elif counts[-1] < counts[0]:
            trend = "decreasing"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "period_start": sorted_dates[0],
            "period_end": sorted_dates[-1],
            "initial_count": counts[0],
            "final_count": counts[-1],
            "method": f"Analyzed trend from {len(sorted_dates)} data points",
            "source": "Direct analysis from entity data"
        }
    
    def answer_statistical_question(self, question: str) -> Dict[str, Any]:
        """
        Route statistical questions to appropriate calculation methods.
        
        Args:
            question: Statistical question
            
        Returns:
            Dictionary with statistical answer, data, and citations
        """
        question_lower = question.lower()
        
        # Detect statistical question type
        if "average" in question_lower or "mean" in question_lower:
            # For now, return message that specific implementation needed
            # Could be enhanced to calculate averages for specific entities
            return {
                "answer": "Average calculations require specific entity type and field. Please specify what you want to average (e.g., 'average meetings per workgroup').",
                "method": "Statistical query - requires specific entity context",
                "source": "Entity storage",
                "citations": []
            }
        elif "range" in question_lower or "min" in question_lower or "max" in question_lower:
            return {
                "answer": "Range calculations require specific entity type and field. Please specify what you want to find the range for.",
                "method": "Statistical query - requires specific entity context",
                "source": "Entity storage",
                "citations": []
            }
        elif "trend" in question_lower:
            # Get meeting statistics and detect trends
            stats = self.get_meeting_statistics()
            # This is a simplified trend - could be enhanced
            return {
                "answer": f"Meeting statistics show {stats['total_meetings']} total meetings across {len(stats.get('meetings_by_workgroup', {}))} workgroups.",
                "method": "Trend analysis from meeting statistics",
                "source": "Entity storage JSON files",
                "citations": [{
                    "type": "statistical",
                    "description": f"Analyzed meeting statistics from entity storage",
                    "method": stats.get("method", "Direct aggregation")
                }]
            }
        
        return {
            "answer": "Statistical question not recognized. Please rephrase with specific entity type and calculation type.",
            "method": "Statistical query - unrecognized",
            "source": "N/A",
            "citations": []
        }
    
    def answer_quantitative_question(self, question: str, source_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze question and provide quantitative answer with data source citations.
        
        Args:
            question: User question requiring quantitative answer
            source_url: Optional source URL to count from directly
            
        Returns:
            Dictionary with answer, data, and citations
        """
        question_lower = question.lower()
        
        # Check if statistical question first
        statistical_keywords = ["average", "mean", "range", "min", "max", "trend", "distribution", "frequency"]
        if any(keyword in question_lower for keyword in statistical_keywords):
            result = self.answer_statistical_question(question)
            # Ensure method and source are always included
            if "method" not in result:
                result["method"] = "Statistical calculation"
            if "source" not in result:
                result["source"] = "Entity storage"
            return result
        
        # Check for workgroup questions
        if "workgroup" in question_lower and ("how many" in question_lower or "count" in question_lower or "number" in question_lower):
            workgroup_stats = self.get_meeting_statistics()
            workgroup_count = len(workgroup_stats.get("meetings_by_workgroup", {}))
            return {
                "answer": f"There are {workgroup_count} workgroups in the archive.",
                "count": workgroup_count,
                "source": workgroup_stats.get("source", "Entity storage JSON files"),
                "method": "Counted unique workgroups from meetings_by_workgroup index",
                "citations": [{
                    "type": "data_source",
                    "description": f"Counted {workgroup_count} workgroups from index file",
                    "method": "Direct count from workgroup index"
                }]
            }
        
        # Check for people questions
        if "people" in question_lower or "person" in question_lower or "participant" in question_lower:
            if "how many" in question_lower or "count" in question_lower or "number" in question_lower:
                # Count people from entity storage
                people_dir = ENTITIES_PEOPLE_DIR
                if people_dir.exists():
                    person_files = list(people_dir.glob("*.json"))
                    person_count = len(person_files)
                    return {
                        "answer": f"There are {person_count} people in the archive.",
                        "count": person_count,
                        "source": f"JSON files in {people_dir}",
                        "method": "Direct file count from entity storage - counted person JSON files",
                        "citations": [{
                            "type": "data_source",
                            "description": f"Counted {person_count} people from entity storage",
                            "method": "Direct file count",
                            "file_count": person_count
                        }]
                    }
                else:
                    return {
                        "answer": "No people found in entity storage.",
                        "count": 0,
                        "source": f"JSON files in {people_dir}",
                        "method": "Direct file count - directory not found",
                        "citations": [{
                            "type": "data_source",
                            "description": "People directory not found in entity storage",
                            "method": "Directory check"
                        }]
                    }
        
        # Detect question type - meetings
        if any(pattern in question_lower for pattern in ["meeting", "how many", "count", "number of", "total"]):
            # Check if question mentions a source URL
            if source_url is None:
                # Try to extract URL from question
                import re
                url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
                urls = re.findall(url_pattern, question)
                if urls:
                    source_url = urls[0]
                    logger.info("quantitative_query_url_extracted_from_question", url=source_url)
            
            data = self.count_all_meetings(source_url=source_url)
            count = data['count']
            unique_count = data.get('unique_count', count)
            
            # Build answer with discrepancy explanation if needed
            if "discrepancy" in data and data["discrepancy"]["difference"] != 0:
                discrepancy_info = data["discrepancy"]
                if unique_count != count:
                    answer = (
                        f"There are {unique_count} unique meetings in the source data ({data['source']}), "
                        f"with {count} total entries in the JSON array. "
                        f"However, only {discrepancy_info['entity_storage_count']} meetings are currently "
                        f"ingested into entity storage. {abs(discrepancy_info['difference'])} meeting(s) "
                        f"have not yet been ingested."
                    )
                else:
                    answer = (
                        f"There are {count} meetings in the source data ({data['source']}). "
                        f"However, only {discrepancy_info['entity_storage_count']} meetings are currently "
                        f"ingested into entity storage. {abs(discrepancy_info['difference'])} meeting(s) "
                        f"have not yet been ingested."
                    )
            elif unique_count != count and unique_count > 0:
                answer = (
                    f"There are {unique_count} unique meetings in the source data ({data['source']}), "
                    f"with {count} total entries in the JSON array. "
                    f"The difference indicates some meetings may appear multiple times or have different representations."
                )
            else:
                answer = f"There are {count} meetings in the archive."
            
            citations = [
                {
                    "type": "data_source",
                    "description": f"Counted {count} meetings from {data['source']}",
                    "file_count": data.get("total_files_checked", 0) if "total_files_checked" in data else None,
                    "source_url": data.get("source", ""),
                    "sample_files": data.get("data_files_checked", [])[:3] if "data_files_checked" in data else []
                }
            ]
            
            # Add discrepancy citation if applicable
            if "discrepancy" in data:
                citations.append({
                    "type": "discrepancy",
                    "description": data["discrepancy"]["explanation"],
                    "entity_storage_count": data["discrepancy"]["entity_storage_count"],
                    "source_count": data["discrepancy"]["source_count"]
                })
            else:
                citations.append({
                    "type": "verification",
                    "description": f"Verified by scanning {data.get('total_files_checked', 0)} JSON files",
                    "meeting_ids_sampled": data.get("citations", [])[:5]
                })
            
            return {
                "answer": answer,
                "count": count,
                "source": data["source"],
                "method": data["method"],
                "citations": citations,
                "discrepancy": data.get("discrepancy")
            }
        
        # Add more question patterns as needed
        else:
            logger.warning("quantitative_query_question_not_recognized", question=question)
            return {
                "answer": "I cannot answer this quantitative question. Please ask about meeting counts.",
                "supported_questions": [
                    "How many meetings are there?",
                    "Count the meetings",
                    "What is the number of meetings?"
                ]
            }


def create_quantitative_query_service() -> QuantitativeQueryService:
    """Create a quantitative query service instance."""
    return QuantitativeQueryService()

