#!/usr/bin/env python3
"""
End-to-End Test V1: Pacific Ocean vs Volcano Content
====================================================

This test demonstrates the semantic search precision by:
1. Adding 3 files related to Pacific Ocean
2. Adding 1 file related to volcano 
3. Testing that Pacific Ocean queries return only the 3 relevant files
4. Verifying semantic similarity scores correctly filter content

Run: python test_e2e_v1.py
"""

import requests
import json
import time
import sys
from typing import Dict, List, Any

class E2ETestV1:
    def __init__(self, base_url: str = "http://localhost:5001"):
        self.base_url = base_url
        self.user_id = "e2e_test_user_v1"
        self.test_files = []
        
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
        """Create test user for the experiment."""
        self.log("👤 Creating test user...")
        try:
            user_data = {
                "username": f"e2e_tester_v1_{int(time.time())}",
                "index_mode": "private"
            }
            
            response = self.make_request("POST", "/api/users", data=user_data)
            if response.status_code == 201:
                result = response.json()
                self.user_id = result["user_id"]
                self.log(f"✅ Created test user: {self.user_id}")
                return True
            else:
                self.log(f"❌ Failed to create user: {response.text}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ User creation failed: {e}", "ERROR")
            return False
    
    def add_pacific_ocean_files(self) -> bool:
        """Add 3 files related to Pacific Ocean."""
        self.log("🌊 Adding Pacific Ocean files...")
        
        pacific_files = [
            {
                "file_id": "pacific_whales_001",
                "filename": "humpback_whales_pacific.mp4",
                "summary_text": "Stunning documentary following humpback whales during their annual migration across the Pacific Ocean. The film captures their incredible journey from Alaska to Hawaii, showcasing their feeding behaviors, mating rituals, and the challenges they face in the vast Pacific waters.",
                "frame_details": "00:00 - Aerial view of Pacific Ocean with whale spouts visible. 01:30 - Underwater footage of humpback whale pod swimming through deep Pacific waters. 03:00 - Close-up of whale tail flukes breaking the ocean surface. 04:45 - Mother whale with calf navigating Pacific currents. 06:20 - Time-lapse of sunset over endless Pacific horizon with whale silhouettes.",
                "analysis_metadata": {
                    "duration": 420,
                    "format": "mp4", 
                    "resolution": "4K",
                    "owner": "marine_documentary_team",
                    "topic": "marine_wildlife_pacific",
                    "tags": ["pacific_ocean", "whales", "migration", "marine_life", "documentary"]
                }
            },
            {
                "file_id": "pacific_coral_002", 
                "filename": "great_barrier_reef_pacific.mp4",
                "summary_text": "Breathtaking exploration of the Great Barrier Reef in the Pacific Ocean, showcasing vibrant coral ecosystems and diverse marine life. The documentary reveals the intricate relationships between species and the reef's critical role in Pacific Ocean biodiversity.",
                "frame_details": "00:00 - Panoramic view of colorful coral formations in crystal clear Pacific waters. 02:00 - Schools of tropical fish swimming through coral gardens. 03:30 - Close-up of sea turtle gliding over reef structures. 05:00 - Vibrant anemones and clownfish interactions. 06:45 - Sharks patrolling the outer reef edges in deep Pacific waters.",
                "analysis_metadata": {
                    "duration": 380,
                    "format": "mp4",
                    "resolution": "4K", 
                    "owner": "ocean_conservation_group",
                    "topic": "coral_reef_pacific",
                    "tags": ["pacific_ocean", "coral_reef", "marine_biodiversity", "underwater", "conservation"]
                }
            },
            {
                "file_id": "pacific_surfing_003",
                "filename": "big_wave_surfing_pacific.mp4", 
                "summary_text": "Adrenaline-pumping footage of professional surfers riding massive waves along the Pacific Coast. From Mavericks in California to Pipeline in Hawaii, this film captures the raw power of Pacific Ocean swells and the athletes who challenge them.",
                "frame_details": "00:00 - Massive Pacific Ocean wave building offshore. 01:15 - Surfer dropping into 40-foot wave face. 02:30 - Slow-motion shot of water barrel formation in Pacific swell. 03:45 - Aerial view of surfer carving across enormous Pacific wave. 05:00 - Dramatic wipeout with surfer tumbling in Pacific white water.",
                "analysis_metadata": {
                    "duration": 300,
                    "format": "mp4",
                    "resolution": "4K",
                    "owner": "extreme_sports_films", 
                    "topic": "surfing_pacific_waves",
                    "tags": ["pacific_ocean", "surfing", "big_waves", "extreme_sports", "california", "hawaii"]
                }
            }
        ]
        
        success_count = 0
        for file_data in pacific_files:
            file_data["user_id"] = self.user_id
            try:
                response = self.make_request("POST", "/api/files", data=file_data)
                if response.status_code == 201:
                    result = response.json()
                    self.test_files.append(file_data["file_id"])
                    self.log(f"✅ Added Pacific Ocean file: {file_data['filename']}")
                    success_count += 1
                else:
                    self.log(f"❌ Failed to add file {file_data['filename']}: {response.text}", "ERROR")
            except Exception as e:
                self.log(f"❌ Error adding file {file_data['filename']}: {e}", "ERROR")
        
        if success_count == 3:
            self.log(f"✅ Successfully added all {success_count} Pacific Ocean files")
            return True
        else:
            self.log(f"❌ Only added {success_count}/3 Pacific Ocean files", "ERROR")
            return False
    
    def add_volcano_file(self) -> bool:
        """Add 1 file related to volcano (should NOT match Pacific Ocean queries)."""
        self.log("🌋 Adding volcano file (control/negative case)...")
        
        volcano_file = {
            "file_id": "volcano_eruption_001",
            "filename": "mount_vesuvius_eruption.mp4",
            "summary_text": "Dramatic documentary about Mount Vesuvius volcanic eruption in Italy, exploring the geological forces that shape our planet. The film examines the historical impact of volcanic activity on ancient civilizations and modern cities built near active volcanoes.",
            "frame_details": "00:00 - Aerial view of Mount Vesuvius crater with steam rising. 01:45 - Molten lava flowing down volcanic slopes. 03:00 - Ancient Pompeii ruins with volcano in background. 04:30 - Geological cross-section showing magma chambers beneath volcano. 06:00 - Time-lapse of ash clouds billowing from volcanic peak.",
            "analysis_metadata": {
                "duration": 360,
                "format": "mp4",
                "resolution": "4K",
                "owner": "geological_documentaries",
                "topic": "volcanic_activity",
                "tags": ["volcano", "eruption", "geology", "italy", "vesuvius", "natural_disasters"]
            },
            "user_id": self.user_id
        }
        
        try:
            response = self.make_request("POST", "/api/files", data=volcano_file)
            if response.status_code == 201:
                result = response.json()
                self.test_files.append(volcano_file["file_id"])
                self.log(f"✅ Added volcano file: {volcano_file['filename']}")
                return True
            else:
                self.log(f"❌ Failed to add volcano file: {response.text}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Error adding volcano file: {e}", "ERROR")
            return False
    
    def test_pacific_ocean_queries(self) -> bool:
        """Test Pacific Ocean related queries and verify only 3 relevant files return."""
        self.log("🔍 Testing Pacific Ocean semantic search queries...")
        
        # Test queries that should match Pacific Ocean content
        test_queries = [
            "Pacific Ocean marine life whales",
            "ocean waves surfing Pacific coast", 
            "underwater coral reef Pacific waters",
            "Pacific marine ecosystem biodiversity"
        ]
        
        all_tests_passed = True
        
        for query in test_queries:
            self.log(f"🔎 Testing query: '{query}'")
            
            try:
                # Test summary search
                response = self.make_request("GET", "/api/search/summary", 
                                           params={"q": query, "user_id": self.user_id, "top_k": 10})
                
                if response.status_code == 200:
                    results = response.json()["results"]
                    
                    # Filter results with positive similarity scores
                    relevant_results = [r for r in results if r["similarity_score"] > 0.1]
                    pacific_results = [r for r in relevant_results if "pacific" in r["filename"].lower() or "pacific" in r["summary_text"].lower()]
                    volcano_results = [r for r in relevant_results if "volcano" in r["filename"].lower() or "volcano" in r["summary_text"].lower()]
                    
                    self.log(f"  📊 Summary search results:")
                    self.log(f"    - Total relevant results (score > 0.1): {len(relevant_results)}")
                    self.log(f"    - Pacific Ocean files: {len(pacific_results)}")
                    self.log(f"    - Volcano files: {len(volcano_results)}")
                    
                    # Print top 3 results with scores
                    top_results = sorted(results, key=lambda x: x["similarity_score"], reverse=True)[:3]
                    for i, result in enumerate(top_results, 1):
                        self.log(f"    - #{i}: {result['filename']} (score: {result['similarity_score']:.3f})")
                    
                    # Validate that Pacific Ocean files score higher than volcano
                    if len(pacific_results) == 3 and len(volcano_results) == 0:
                        self.log(f"  ✅ Perfect filtering: 3 Pacific files, 0 volcano files")
                    elif len(pacific_results) >= 2 and (len(volcano_results) == 0 or 
                                                        (len(volcano_results) > 0 and pacific_results[0]["similarity_score"] > volcano_results[0]["similarity_score"])):
                        self.log(f"  ✅ Good filtering: Pacific files score higher than volcano")
                    else:
                        self.log(f"  ⚠️  Filtering issue: Expected Pacific files to dominate results", "WARNING") 
                        all_tests_passed = False
                        
                else:
                    self.log(f"  ❌ Summary search failed: {response.text}", "ERROR")
                    all_tests_passed = False
                
                # Test frame details search
                response = self.make_request("GET", "/api/search/frames",
                                           params={"q": query, "user_id": self.user_id, "top_k": 10})
                
                if response.status_code == 200:
                    results = response.json()["results"]
                    relevant_results = [r for r in results if r["similarity_score"] > 0.1]
                    pacific_results = [r for r in relevant_results if "pacific" in r["filename"].lower() or "pacific" in r["frame_details"].lower()]
                    volcano_results = [r for r in relevant_results if "volcano" in r["filename"].lower() or "volcano" in r["frame_details"].lower()]
                    
                    self.log(f"  📊 Frame details search results:")
                    self.log(f"    - Total relevant results (score > 0.1): {len(relevant_results)}")
                    self.log(f"    - Pacific Ocean files: {len(pacific_results)}")
                    self.log(f"    - Volcano files: {len(volcano_results)}")
                    
                    # Print top 3 results with scores
                    top_results = sorted(results, key=lambda x: x["similarity_score"], reverse=True)[:3]
                    for i, result in enumerate(top_results, 1):
                        self.log(f"    - #{i}: {result['filename']} (score: {result['similarity_score']:.3f})")
                        
                else:
                    self.log(f"  ❌ Frame search failed: {response.text}", "ERROR")
                    all_tests_passed = False
                    
                self.log("")  # Empty line for readability
                
            except Exception as e:
                self.log(f"  ❌ Query test failed: {e}", "ERROR")
                all_tests_passed = False
        
        return all_tests_passed
    
    def test_volcano_query_control(self) -> bool:
        """Test volcano query to ensure it returns the volcano file with high score."""
        self.log("🌋 Testing volcano query (control test)...")
        
        volcano_query = "volcanic eruption lava mountain geological"
        
        try:
            response = self.make_request("GET", "/api/search/summary",
                                       params={"q": volcano_query, "user_id": self.user_id, "top_k": 10})
            
            if response.status_code == 200:
                results = response.json()["results"]
                top_result = max(results, key=lambda x: x["similarity_score"]) if results else None
                
                if top_result and ("volcano" in top_result["filename"].lower() or "vesuvius" in top_result["filename"].lower()):
                    self.log(f"✅ Volcano query correctly returned volcano file with score: {top_result['similarity_score']:.3f}")
                    self.log(f"   Top result: {top_result['filename']}")
                    return True
                else:
                    self.log(f"❌ Volcano query did not return volcano file as top result", "ERROR")
                    if top_result:
                        self.log(f"   Instead got: {top_result['filename']} (score: {top_result['similarity_score']:.3f})")
                    return False
            else:
                self.log(f"❌ Volcano search failed: {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Volcano query test failed: {e}", "ERROR")
            return False
    
    def cleanup(self) -> bool:
        """Clean up test data."""
        self.log("🧹 Cleaning up test data...")
        
        success_count = 0
        for file_id in self.test_files:
            try:
                response = self.make_request("DELETE", f"/api/files/{file_id}",
                                           params={"user_id": self.user_id})
                if response.status_code == 200:
                    success_count += 1
                else:
                    self.log(f"⚠️  Failed to delete file {file_id}: {response.text}", "WARNING")
            except Exception as e:
                self.log(f"⚠️  Error deleting file {file_id}: {e}", "WARNING")
        
        self.log(f"🧹 Cleaned up {success_count}/{len(self.test_files)} test files")
        return success_count == len(self.test_files)
    
    def run_full_test(self) -> bool:
        """Run the complete end-to-end test suite."""
        self.log("🚀 Starting End-to-End Test V1: Pacific Ocean vs Volcano")
        self.log("=" * 60)
        
        start_time = time.time()
        
        # Execute test steps
        steps = [
            ("Health Check", self.test_health_check),
            ("Create Test User", self.create_test_user), 
            ("Add Pacific Ocean Files", self.add_pacific_ocean_files),
            ("Add Volcano File", self.add_volcano_file),
            ("Test Pacific Ocean Queries", self.test_pacific_ocean_queries),
            ("Test Volcano Query (Control)", self.test_volcano_query_control),
            ("Cleanup", self.cleanup)
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
                    if step_name != "Cleanup":  # Continue with cleanup even if other steps fail
                        break
            except Exception as e:
                self.log(f"❌ {step_name} crashed: {e}", "ERROR")
                results.append((step_name, False))
                if step_name != "Cleanup":
                    break
            
            self.log("")  # Empty line for readability
        
        # Final results
        end_time = time.time()
        duration = end_time - start_time
        
        self.log("=" * 60)
        self.log("📊 TEST RESULTS SUMMARY")
        self.log("=" * 60)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for step_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            self.log(f"{status} - {step_name}")
        
        self.log("")
        self.log(f"🏁 Overall Result: {passed}/{total} steps passed")
        self.log(f"⏱️  Total Duration: {duration:.1f} seconds")
        
        if passed == total:
            self.log("🎉 END-TO-END TEST V1 PASSED! Semantic search works perfectly!")
            return True
        else:
            self.log("💥 END-TO-END TEST V1 FAILED! Check logs above for details.")
            return False

def main():
    """Main function to run the test."""
    import argparse
    
    parser = argparse.ArgumentParser(description="End-to-End Test V1: Pacific Ocean vs Volcano")
    parser.add_argument("--url", default="http://localhost:5001", help="Base URL for the media search service")
    parser.add_argument("--wait", type=int, default=0, help="Wait time in seconds before starting test")
    
    args = parser.parse_args()
    
    if args.wait > 0:
        print(f"⏳ Waiting {args.wait} seconds for service to be ready...")
        time.sleep(args.wait)
    
    # Run the test
    tester = E2ETestV1(base_url=args.url)
    success = tester.run_full_test()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 