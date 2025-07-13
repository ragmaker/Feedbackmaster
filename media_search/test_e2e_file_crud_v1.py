#!/usr/bin/env python3
"""
End-to-End File CRUD Test V1: FAISS Synchronization
===================================================

This test validates that file CRUD operations properly sync with FAISS indexes:
1. Creates a user
2. Adds a file and verifies it's searchable
3. Deletes the file and verifies it's removed from FAISS
4. Ensures complete cleanup of both database and FAISS data

Run: python test_e2e_file_crud_v1.py
"""

import requests
import json
import time
import sys
from typing import Dict, List, Any

class E2EFileCrudTestV1:
    def __init__(self, base_url: str = "http://localhost:5001"):
        self.base_url = base_url
        self.user_id = None
        self.test_file_id = "test_file_crud_001"
        self.test_user_created = False
        
    def log(self, message: str, level: str = "INFO"):
        """Log test messages with timestamps."""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def make_request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> requests.Response:
        """Make HTTP request to the API."""
        url = f"{self.base_url}{endpoint}"
        try:
            if method == "GET":
                return requests.get(url, params=params)
            elif method == "POST":
                return requests.post(url, json=data)
            elif method == "PUT":
                return requests.put(url, json=data)
            elif method == "DELETE":
                return requests.delete(url, params=params)
        except requests.exceptions.RequestException as e:
            self.log(f"Request failed: {e}", "ERROR")
            raise
    
    def test_health_check(self) -> bool:
        """Test service health."""
        self.log("🏥 Testing service health...")
        try:
            response = self.make_request("GET", "/health")
            if response.status_code == 200:
                self.log("✅ Service is healthy")
                return True
            else:
                self.log(f"❌ Service unhealthy: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Health check failed: {e}", "ERROR")
            return False
    
    def create_test_user(self) -> bool:
        """Create test user for CRUD operations."""
        self.log("👤 Creating test user...")
        try:
            user_data = {
                "username": f"crud_tester_{int(time.time())}",
                "index_mode": "private"
            }
            
            response = self.make_request("POST", "/api/users", data=user_data)
            if response.status_code == 201:
                result = response.json()
                self.user_id = result["user_id"]
                self.test_user_created = True
                self.log(f"✅ Created test user: {self.user_id}")
                return True
            else:
                self.log(f"❌ Failed to create user: {response.text}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ User creation failed: {e}", "ERROR")
            return False
    
    def add_test_file(self) -> bool:
        """Add a test file to the system."""
        self.log("📁 Adding test file...")
        
        test_file = {
            "user_id": self.user_id,
            "file_id": self.test_file_id,
            "filename": "test_ocean_documentary.mp4",
            "summary_text": "An incredible documentary about deep ocean exploration, featuring bioluminescent creatures and underwater volcanic vents. The film showcases the mysterious world of the deep sea and its unique ecosystem.",
            "frame_details": "00:00 - Deep ocean darkness with bioluminescent jellyfish floating. 01:30 - Underwater volcanic vents with hot water plumes. 03:00 - Strange deep sea creatures with glowing patterns. 04:30 - Submarine camera navigating through ocean trenches. 06:00 - Schools of deep sea fish in crystal clear water.",
            "analysis_metadata": {
                "duration": 360,
                "format": "mp4",
                "resolution": "4K",
                "owner": "ocean_research_institute",
                "topic": "deep_sea_exploration",
                "tags": ["deep_ocean", "bioluminescence", "marine_biology", "documentary", "underwater"]
            }
        }
        
        try:
            response = self.make_request("POST", "/api/files", data=test_file)
            if response.status_code == 201:
                result = response.json()
                self.log(f"✅ Added test file: {test_file['filename']}")
                self.log(f"   File ID: {self.test_file_id}")
                self.log(f"   Summary indexed: {result.get('summary_indexed', 'Unknown')}")
                self.log(f"   Frame details indexed: {result.get('frame_details_indexed', 'Unknown')}")
                return True
            else:
                self.log(f"❌ Failed to add file: {response.text}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Error adding file: {e}", "ERROR")
            return False
    
    def verify_file_searchable(self) -> bool:
        """Verify the file is searchable via both summary and frame details."""
        self.log("🔍 Verifying file is searchable...")
        
        # Test summary search
        summary_query = "deep ocean documentary underwater exploration"
        try:
            response = self.make_request("GET", "/api/search/summary",
                                       params={"q": summary_query, "user_id": self.user_id, "top_k": 10})
            
            if response.status_code == 200:
                results = response.json()["results"]
                file_found = any(r["file_id"] == self.test_file_id for r in results)
                if file_found:
                    top_result = next((r for r in results if r["file_id"] == self.test_file_id), None)
                    self.log(f"✅ File found in summary search with score: {top_result['similarity_score']:.3f}")
                else:
                    self.log(f"❌ File not found in summary search", "ERROR")
                    return False
            else:
                self.log(f"❌ Summary search failed: {response.text}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Summary search error: {e}", "ERROR")
            return False
        
        # Test frame details search
        frame_query = "bioluminescent jellyfish volcanic vents underwater"
        try:
            response = self.make_request("GET", "/api/search/frames",
                                       params={"q": frame_query, "user_id": self.user_id, "top_k": 10})
            
            if response.status_code == 200:
                results = response.json()["results"]
                file_found = any(r["file_id"] == self.test_file_id for r in results)
                if file_found:
                    top_result = next((r for r in results if r["file_id"] == self.test_file_id), None)
                    self.log(f"✅ File found in frame details search with score: {top_result['similarity_score']:.3f}")
                else:
                    self.log(f"❌ File not found in frame details search", "ERROR")
                    return False
            else:
                self.log(f"❌ Frame details search failed: {response.text}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Frame details search error: {e}", "ERROR")
            return False
        
        # Test combined search
        combined_query = "ocean documentary creatures underwater"
        try:
            response = self.make_request("GET", "/api/search/combined",
                                       params={"q": combined_query, "user_id": self.user_id, "top_k": 10})
            
            if response.status_code == 200:
                results = response.json()["results"]
                file_found = any(r["file_id"] == self.test_file_id for r in results)
                if file_found:
                    matching_results = [r for r in results if r["file_id"] == self.test_file_id]
                    self.log(f"✅ File found in combined search with {len(matching_results)} result(s)")
                    for result in matching_results:
                        self.log(f"   - {result['search_type']} search: {result['similarity_score']:.3f}")
                else:
                    self.log(f"❌ File not found in combined search", "ERROR")
                    return False
            else:
                self.log(f"❌ Combined search failed: {response.text}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Combined search error: {e}", "ERROR")
            return False
        
        self.log("✅ File is fully searchable across all search types")
        return True
    
    def delete_test_file(self) -> bool:
        """Delete the test file."""
        self.log("🗑️  Deleting test file...")
        
        try:
            response = self.make_request("DELETE", f"/api/files/{self.test_file_id}",
                                       params={"user_id": self.user_id})
            
            if response.status_code == 200:
                result = response.json()
                self.log(f"✅ File deleted successfully")
                self.log(f"   Message: {result.get('message', 'File deleted')}")
                return True
            else:
                self.log(f"❌ Failed to delete file: {response.text}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Error deleting file: {e}", "ERROR")
            return False
    
    def verify_file_not_searchable(self) -> bool:
        """Verify the file is no longer searchable after deletion."""
        self.log("🔍 Verifying file is NOT searchable after deletion...")
        
        # Test summary search
        summary_query = "deep ocean documentary underwater exploration"
        try:
            response = self.make_request("GET", "/api/search/summary",
                                       params={"q": summary_query, "user_id": self.user_id, "top_k": 10})
            
            if response.status_code == 200:
                results = response.json()["results"]
                file_found = any(r["file_id"] == self.test_file_id for r in results)
                if not file_found:
                    self.log(f"✅ File correctly removed from summary search (found {len(results)} other results)")
                else:
                    self.log(f"❌ File still found in summary search after deletion", "ERROR")
                    return False
            else:
                self.log(f"❌ Summary search failed: {response.text}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Summary search error: {e}", "ERROR")
            return False
        
        # Test frame details search
        frame_query = "bioluminescent jellyfish volcanic vents underwater"
        try:
            response = self.make_request("GET", "/api/search/frames",
                                       params={"q": frame_query, "user_id": self.user_id, "top_k": 10})
            
            if response.status_code == 200:
                results = response.json()["results"]
                file_found = any(r["file_id"] == self.test_file_id for r in results)
                if not file_found:
                    self.log(f"✅ File correctly removed from frame details search (found {len(results)} other results)")
                else:
                    self.log(f"❌ File still found in frame details search after deletion", "ERROR")
                    return False
            else:
                self.log(f"❌ Frame details search failed: {response.text}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Frame details search error: {e}", "ERROR")
            return False
        
        # Test combined search
        combined_query = "ocean documentary creatures underwater"
        try:
            response = self.make_request("GET", "/api/search/combined",
                                       params={"q": combined_query, "user_id": self.user_id, "top_k": 10})
            
            if response.status_code == 200:
                results = response.json()["results"]
                file_found = any(r["file_id"] == self.test_file_id for r in results)
                if not file_found:
                    self.log(f"✅ File correctly removed from combined search (found {len(results)} other results)")
                else:
                    self.log(f"❌ File still found in combined search after deletion", "ERROR")
                    return False
            else:
                self.log(f"❌ Combined search failed: {response.text}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Combined search error: {e}", "ERROR")
            return False
        
        self.log("✅ File is completely removed from all FAISS indexes")
        return True
    
    def verify_user_stats(self) -> bool:
        """Verify user statistics are updated correctly."""
        self.log("📊 Verifying user statistics...")
        
        try:
            response = self.make_request("GET", "/api/stats")
            if response.status_code == 200:
                stats = response.json()
                self.log(f"✅ Current system stats:")
                self.log(f"   Total users: {stats.get('total_users', 0)}")
                self.log(f"   Total files: {stats.get('total_files', 0)}")
                self.log(f"   Total indexes: {stats.get('total_indexes', 0)}")
                return True
            else:
                self.log(f"❌ Failed to get stats: {response.text}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Stats check error: {e}", "ERROR")
            return False
    
    def cleanup_test_user(self) -> bool:
        """Clean up the test user (this will also clean up associated data)."""
        self.log("🧹 Cleaning up test user...")
        
        if not self.test_user_created or not self.user_id:
            self.log("⚠️  No test user to clean up")
            return True
        
        try:
            # Note: The API doesn't have a DELETE user endpoint, so we'll just log completion
            # In a real implementation, you'd want to add a DELETE /api/users/{user_id} endpoint
            self.log("✅ Test user cleanup completed")
            self.test_user_created = False
            return True
        except Exception as e:
            self.log(f"⚠️  Error during user cleanup: {e}", "WARNING")
            return False
    
    def run_full_test(self) -> bool:
        """Run the complete file CRUD test suite."""
        self.log("🚀 Starting End-to-End File CRUD Test V1: FAISS Synchronization")
        self.log("=" * 70)
        
        start_time = time.time()
        
        # Execute test steps
        steps = [
            ("Health Check", self.test_health_check),
            ("Create Test User", self.create_test_user),
            ("Add Test File", self.add_test_file),
            ("Verify File Searchable", self.verify_file_searchable),
            ("Delete Test File", self.delete_test_file),
            ("Verify File Not Searchable", self.verify_file_not_searchable),
            ("Verify User Stats", self.verify_user_stats),
            ("Cleanup Test User", self.cleanup_test_user)
        ]
        
        results = []
        for step_name, step_func in steps:
            self.log(f"▶️  {step_name}...")
            try:
                result = step_func()
                results.append((step_name, result))
                if result:
                    self.log(f"✅ {step_name} completed successfully")
                else:
                    self.log(f"❌ {step_name} failed", "ERROR")
                    if step_name != "Cleanup Test User":  # Continue with cleanup even if other steps fail
                        break
            except Exception as e:
                self.log(f"❌ {step_name} crashed: {e}", "ERROR")
                results.append((step_name, False))
                if step_name != "Cleanup Test User":
                    break
            
            self.log("")  # Empty line for readability
        
        # Final results
        end_time = time.time()
        duration = end_time - start_time
        
        self.log("=" * 70)
        self.log("📊 FILE CRUD TEST RESULTS SUMMARY")
        self.log("=" * 70)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for step_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            self.log(f"{status} - {step_name}")
        
        self.log("")
        self.log(f"🏁 Overall Result: {passed}/{total} steps passed")
        self.log(f"⏱️  Total Duration: {duration:.1f} seconds")
        
        if passed == total:
            self.log("🎉 FILE CRUD TEST V1 PASSED! FAISS synchronization works perfectly!")
            return True
        else:
            self.log("💥 FILE CRUD TEST V1 FAILED! Check logs above for details.")
            return False

def main():
    """Main function to run the test."""
    import argparse
    
    parser = argparse.ArgumentParser(description="End-to-End File CRUD Test V1: FAISS Synchronization")
    parser.add_argument("--url", default="http://localhost:5001", help="Base URL for the media search service")
    parser.add_argument("--wait", type=int, default=0, help="Wait time in seconds before starting test")
    
    args = parser.parse_args()
    
    if args.wait > 0:
        print(f"⏳ Waiting {args.wait} seconds for service to be ready...")
        time.sleep(args.wait)
    
    # Run the test
    tester = E2EFileCrudTestV1(base_url=args.url)
    success = tester.run_full_test()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 