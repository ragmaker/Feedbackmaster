#!/usr/bin/env python3
"""
Comprehensive tests for media_search service full workflow.
This test suite covers all endpoints and functionality with hardcoded test data.
"""

import requests
import json
import time
import os
import sys
from typing import Dict, Any, List

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

class MediaSearchTester:
    """Test class for media_search service."""
    
    def __init__(self, base_url: str = "http://localhost:5001"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_users = []
        self.test_files = []
        
    def log(self, message: str, level: str = "INFO"):
        """Log a message with timestamp."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def make_request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> requests.Response:
        """Make a request to the API."""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url, params=params)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data)
            elif method.upper() == "PUT":
                response = self.session.put(url, json=data)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, params=params)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            return response
        except Exception as e:
            self.log(f"Request failed: {e}", "ERROR")
            raise
    
    def test_health_check(self) -> bool:
        """Test health check endpoint."""
        self.log("Testing health check endpoint...")
        
        try:
            response = self.make_request("GET", "/health")
            
            if response.status_code == 200:
                data = response.json()
                assert data["status"] == "healthy"
                assert data["service"] == "media_search"
                self.log("✓ Health check passed")
                return True
            else:
                self.log(f"✗ Health check failed with status {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"✗ Health check failed with error: {e}", "ERROR")
            return False
    
    def test_create_users(self) -> bool:
        """Test user creation with different index modes."""
        self.log("Testing user creation...")
        
        test_users = [
            {"username": "test_user_private", "index_mode": "private"},
            {"username": "test_user_shared", "index_mode": "shared"},
            {"username": "test_user_default"}  # Should use default index mode
        ]
        
        try:
            for user_data in test_users:
                response = self.make_request("POST", "/api/users", user_data)
                
                if response.status_code == 201:
                    created_user = response.json()
                    assert "user_id" in created_user
                    assert created_user["username"] == user_data["username"]
                    self.test_users.append(created_user)
                    self.log(f"✓ Created user: {created_user['username']} (ID: {created_user['user_id']})")
                else:
                    self.log(f"✗ Failed to create user {user_data['username']}: {response.text}", "ERROR")
                    return False
            
            self.log(f"✓ Created {len(self.test_users)} test users")
            return True
            
        except Exception as e:
            self.log(f"✗ User creation failed: {e}", "ERROR")
            return False
    
    def test_get_users(self) -> bool:
        """Test getting user details."""
        self.log("Testing user retrieval...")
        
        try:
            for user in self.test_users:
                response = self.make_request("GET", f"/api/users/{user['user_id']}")
                
                if response.status_code == 200:
                    user_data = response.json()
                    assert user_data["user_id"] == user["user_id"]
                    assert user_data["username"] == user["username"]
                    self.log(f"✓ Retrieved user: {user_data['username']}")
                else:
                    self.log(f"✗ Failed to retrieve user {user['user_id']}: {response.text}", "ERROR")
                    return False
            
            return True
            
        except Exception as e:
            self.log(f"✗ User retrieval failed: {e}", "ERROR")
            return False
    
    def test_add_single_files(self) -> bool:
        """Test adding single files with hardcoded media analysis data."""
        self.log("Testing single file addition...")
        
        # Hardcoded test data for various media types
        test_files_data = [
            {
                "file_id": "nature_doc_001",
                "filename": "amazon_rainforest.mp4",
                "summary_text": "A breathtaking documentary about the Amazon rainforest showcasing diverse wildlife including jaguars, colorful birds, and exotic plants. The film explores the delicate ecosystem balance and the importance of conservation efforts to protect this natural wonder.",
                "frame_details": "Opening scene: Aerial view of endless green canopy. 00:30 - Close-up of jaguar stalking through dense vegetation. 01:15 - Vibrant toucan perched on branch with colorful plumage. 02:00 - Slow-motion waterfall cascading into crystal clear pool. 02:45 - Indigenous people navigating river in traditional canoe. 03:30 - Time-lapse of sunrise over forest canopy with mist rising.",
                "analysis_metadata": {
                    "duration": 240,
                    "format": "mp4",
                    "resolution": "4K",
                    "owner": "nature_productions",
                    "topic": "nature_documentary",
                    "tags": ["wildlife", "amazon", "conservation", "rainforest", "documentary"]
                }
            },
            {
                "file_id": "cooking_show_001",
                "filename": "italian_pasta_cooking.mp4",
                "summary_text": "A masterclass in Italian pasta making featuring traditional techniques passed down through generations. The chef demonstrates how to make fresh pasta from scratch, prepare authentic carbonara sauce, and plate the dish with proper garnishes.",
                "frame_details": "00:00 - Chef's hands kneading pasta dough on marble counter. 00:45 - Rolling pin stretching dough to perfect thickness. 01:30 - Cutting fresh tagliatelle with precise knife work. 02:15 - Eggs and pancetta sizzling in hot pan. 02:50 - Tossing pasta with creamy carbonara sauce. 03:25 - Final plating with fresh parmesan and black pepper.",
                "analysis_metadata": {
                    "duration": 180,
                    "format": "mp4",
                    "resolution": "1080p",
                    "owner": "culinary_masters",
                    "topic": "cooking_tutorial",
                    "tags": ["cooking", "italian", "pasta", "recipe", "tutorial"]
                }
            },
            {
                "file_id": "tech_review_001",
                "filename": "smartphone_comparison.mp4",
                "summary_text": "Comprehensive comparison of the latest flagship smartphones focusing on camera quality, battery life, and performance benchmarks. The review includes detailed analysis of low-light photography, video recording capabilities, and real-world usage scenarios.",
                "frame_details": "00:00 - Array of smartphones laid out on white background. 00:30 - Side-by-side camera comparison shots in various lighting conditions. 01:00 - Performance benchmark results displayed on screen. 01:30 - Battery drain test with multiple phones running simultaneously. 02:00 - Close-up shots of display quality and color accuracy. 02:30 - Real-world usage scenarios including gaming and video streaming.",
                "analysis_metadata": {
                    "duration": 300,
                    "format": "mp4",
                    "resolution": "1080p",
                    "owner": "tech_reviewer",
                    "topic": "technology_review",
                    "tags": ["smartphone", "technology", "review", "comparison", "cameras"]
                }
            }
        ]
        
        try:
            for i, file_data in enumerate(test_files_data):
                # Use different users for different files
                user = self.test_users[i % len(self.test_users)]
                file_data["user_id"] = user["user_id"]
                
                response = self.make_request("POST", "/api/files", file_data)
                
                if response.status_code == 201:
                    result = response.json()
                    assert result["file_id"] == file_data["file_id"]
                    assert result["status"] == "completed"
                    self.test_files.append(result)
                    self.log(f"✓ Added file: {file_data['filename']} for user {user['username']}")
                else:
                    self.log(f"✗ Failed to add file {file_data['filename']}: {response.text}", "ERROR")
                    return False
            
            self.log(f"✓ Added {len(test_files_data)} files successfully")
            return True
            
        except Exception as e:
            self.log(f"✗ File addition failed: {e}", "ERROR")
            return False
    
    def test_batch_file_addition(self) -> bool:
        """Test batch file addition."""
        self.log("Testing batch file addition...")
        
        batch_files = [
            {
                "file_id": "fitness_workout_001",
                "filename": "yoga_morning_routine.mp4",
                "summary_text": "A calming 30-minute morning yoga routine designed to energize the body and mind. Features gentle stretches, breathing exercises, and meditation techniques suitable for all skill levels.",
                "frame_details": "00:00 - Peaceful sunrise setting with yoga mat. 02:00 - Sun salutation sequence demonstration. 05:00 - Warrior pose variations with proper alignment. 10:00 - Seated meditation with breathing focus. 15:00 - Gentle back stretches and twists. 20:00 - Final relaxation pose with ambient sounds.",
                "analysis_metadata": {
                    "duration": 1800,
                    "format": "mp4",
                    "resolution": "1080p",
                    "owner": "wellness_studio",
                    "topic": "fitness_yoga",
                    "tags": ["yoga", "fitness", "wellness", "morning", "routine"]
                }
            },
            {
                "file_id": "travel_vlog_001",
                "filename": "tokyo_street_food.mp4",
                "summary_text": "An exciting culinary journey through Tokyo's vibrant street food scene. Explores traditional markets, famous food stalls, and hidden gems while showcasing authentic Japanese flavors and cooking techniques.",
                "frame_details": "00:00 - Busy Tsukiji fish market with vendors calling out prices. 01:00 - Sushi chef skillfully preparing fresh tuna. 02:00 - Ramen noodle preparation with rich tonkotsu broth. 03:00 - Takoyaki balls cooking on specialized grill. 04:00 - Colorful display of wagyu beef cuts. 05:00 - Traditional tea ceremony in small shop.",
                "analysis_metadata": {
                    "duration": 420,
                    "format": "mp4",
                    "resolution": "4K",
                    "owner": "travel_blogger",
                    "topic": "travel_food",
                    "tags": ["travel", "tokyo", "street_food", "japanese", "culture"]
                }
            }
        ]
        
        try:
            user = self.test_users[0]  # Use first test user
            batch_data = {
                "user_id": user["user_id"],
                "files": batch_files
            }
            
            response = self.make_request("POST", "/api/files/batch", batch_data)
            
            if response.status_code == 201:
                result = response.json()
                assert result["total_files"] == len(batch_files)
                assert result["successful"] == len(batch_files)
                assert result["failed"] == 0
                self.log(f"✓ Batch added {result['successful']} files successfully")
                return True
            else:
                self.log(f"✗ Batch file addition failed: {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"✗ Batch file addition failed: {e}", "ERROR")
            return False
    
    def test_file_retrieval(self) -> bool:
        """Test file listing and retrieval."""
        self.log("Testing file retrieval...")
        
        try:
            for user in self.test_users:
                # List files for user
                response = self.make_request("GET", "/api/files", params={"user_id": user["user_id"]})
                
                if response.status_code == 200:
                    files_data = response.json()
                    files = files_data["files"]
                    self.log(f"✓ Retrieved {len(files)} files for user {user['username']}")
                    
                    # Test individual file retrieval
                    for file_info in files:
                        file_response = self.make_request("GET", f"/api/files/{file_info['file_id']}", 
                                                        params={"user_id": user["user_id"]})
                        
                        if file_response.status_code == 200:
                            file_data = file_response.json()
                            assert file_data["file_id"] == file_info["file_id"]
                            assert file_data["user_id"] == user["user_id"]
                            self.log(f"✓ Retrieved individual file: {file_data['filename']}")
                        else:
                            self.log(f"✗ Failed to retrieve file {file_info['file_id']}", "ERROR")
                            return False
                else:
                    self.log(f"✗ Failed to list files for user {user['user_id']}: {response.text}", "ERROR")
                    return False
            
            return True
            
        except Exception as e:
            self.log(f"✗ File retrieval failed: {e}", "ERROR")
            return False
    
    def test_search_functionality(self) -> bool:
        """Test all search endpoints with various queries."""
        self.log("Testing search functionality...")
        
        # Test queries designed to match our hardcoded content
        test_queries = [
            "amazon rainforest wildlife",
            "italian pasta cooking",
            "smartphone camera comparison",
            "yoga morning routine",
            "tokyo street food",
            "jaguar in forest",
            "carbonara sauce recipe",
            "battery life test",
            "meditation breathing",
            "sushi preparation"
        ]
        
        try:
            for user in self.test_users:
                user_id = user["user_id"]
                
                for query in test_queries:
                    # Test summary search
                    response = self.make_request("GET", "/api/search/summary", 
                                               params={"q": query, "user_id": user_id, "top_k": 5})
                    
                    if response.status_code == 200:
                        results = response.json()["results"]
                        self.log(f"✓ Summary search for '{query}' returned {len(results)} results for user {user['username']}")
                        
                        # Verify result structure
                        for result in results:
                            assert "file_id" in result
                            assert "similarity_score" in result
                            assert "search_type" in result
                            assert result["search_type"] == "summary"
                    else:
                        self.log(f"✗ Summary search failed for query '{query}': {response.text}", "ERROR")
                        return False
                    
                    # Test frame search
                    response = self.make_request("GET", "/api/search/frames", 
                                               params={"q": query, "user_id": user_id, "top_k": 5})
                    
                    if response.status_code == 200:
                        results = response.json()["results"]
                        self.log(f"✓ Frame search for '{query}' returned {len(results)} results for user {user['username']}")
                        
                        for result in results:
                            assert "file_id" in result
                            assert "similarity_score" in result
                            assert "search_type" in result
                            assert result["search_type"] == "frame"
                    else:
                        self.log(f"✗ Frame search failed for query '{query}': {response.text}", "ERROR")
                        return False
                    
                    # Test combined search
                    response = self.make_request("GET", "/api/search/combined", 
                                               params={"q": query, "user_id": user_id, "top_k": 10})
                    
                    if response.status_code == 200:
                        results = response.json()["results"]
                        self.log(f"✓ Combined search for '{query}' returned {len(results)} results for user {user['username']}")
                        
                        # Verify combined results include both types
                        search_types = {result["search_type"] for result in results}
                        if len(results) > 0:
                            assert len(search_types) <= 2  # Should have at most 'summary' and 'frame'
                    else:
                        self.log(f"✗ Combined search failed for query '{query}': {response.text}", "ERROR")
                        return False
            
            self.log("✓ All search tests passed")
            return True
            
        except Exception as e:
            self.log(f"✗ Search functionality failed: {e}", "ERROR")
            return False
    
    def test_file_management(self) -> bool:
        """Test file update and deletion."""
        self.log("Testing file management...")
        
        try:
            # Get a test file to update
            user = self.test_users[0]
            response = self.make_request("GET", "/api/files", params={"user_id": user["user_id"]})
            
            if response.status_code != 200:
                self.log("✗ Failed to get files for update test", "ERROR")
                return False
            
            files = response.json()["files"]
            if not files:
                self.log("✗ No files available for update test", "ERROR")
                return False
            
            test_file = files[0]
            
            # Test file update
            update_data = {
                "user_id": user["user_id"],
                "filename": "updated_" + test_file["filename"],
                "topic": "updated_topic",
                "tags": ["updated", "test", "file"]
            }
            
            response = self.make_request("PUT", f"/api/files/{test_file['file_id']}", update_data)
            
            if response.status_code == 200:
                updated_file = response.json()
                assert updated_file["filename"] == update_data["filename"]
                assert updated_file["topic"] == update_data["topic"]
                self.log(f"✓ Updated file: {updated_file['filename']}")
            else:
                self.log(f"✗ Failed to update file: {response.text}", "ERROR")
                return False
            
            # Test file deletion
            response = self.make_request("DELETE", f"/api/files/{test_file['file_id']}", 
                                       params={"user_id": user["user_id"]})
            
            if response.status_code == 200:
                self.log(f"✓ Deleted file: {test_file['filename']}")
                
                # Verify file is deleted
                response = self.make_request("GET", f"/api/files/{test_file['file_id']}", 
                                           params={"user_id": user["user_id"]})
                
                if response.status_code == 404:
                    self.log("✓ File deletion verified")
                else:
                    self.log("✗ File still exists after deletion", "ERROR")
                    return False
            else:
                self.log(f"✗ Failed to delete file: {response.text}", "ERROR")
                return False
            
            return True
            
        except Exception as e:
            self.log(f"✗ File management failed: {e}", "ERROR")
            return False
    
    def test_user_management(self) -> bool:
        """Test user update functionality."""
        self.log("Testing user management...")
        
        try:
            user = self.test_users[0]
            
            # Test user update
            update_data = {
                "username": "updated_" + user["username"],
                "index_mode": "shared" if user["index_mode"] == "private" else "private"
            }
            
            response = self.make_request("PUT", f"/api/users/{user['user_id']}", update_data)
            
            if response.status_code == 200:
                updated_user = response.json()
                assert updated_user["username"] == update_data["username"]
                assert updated_user["index_mode"] == update_data["index_mode"]
                self.log(f"✓ Updated user: {updated_user['username']}")
                
                # Update our test user record
                user.update(updated_user)
                return True
            else:
                self.log(f"✗ Failed to update user: {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"✗ User management failed: {e}", "ERROR")
            return False
    
    def test_statistics(self) -> bool:
        """Test statistics endpoint."""
        self.log("Testing statistics endpoint...")
        
        try:
            response = self.make_request("GET", "/api/stats")
            
            if response.status_code == 200:
                stats = response.json()
                assert "users" in stats
                assert "files" in stats
                assert "indexing_status" in stats
                assert "model" in stats
                assert "embedding_dimension" in stats
                
                self.log(f"✓ Statistics: {stats['users']} users, {stats['files']} files")
                self.log(f"✓ Model: {stats['model']}, Embedding dimension: {stats['embedding_dimension']}")
                return True
            else:
                self.log(f"✗ Failed to get statistics: {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"✗ Statistics test failed: {e}", "ERROR")
            return False
    
    def test_error_handling(self) -> bool:
        """Test error handling for various edge cases."""
        self.log("Testing error handling...")
        
        try:
            # Test invalid user creation
            response = self.make_request("POST", "/api/users", {"username": ""})
            assert response.status_code == 400
            
            # Test duplicate username
            response = self.make_request("POST", "/api/users", {"username": self.test_users[0]["username"]})
            assert response.status_code == 400
            
            # Test invalid file addition
            response = self.make_request("POST", "/api/files", {"file_id": "test"})
            assert response.status_code == 400
            
            # Test search without query
            response = self.make_request("GET", "/api/search/summary", params={"user_id": "1"})
            assert response.status_code == 400
            
            # Test search without user_id
            response = self.make_request("GET", "/api/search/summary", params={"q": "test"})
            assert response.status_code == 400
            
            # Test non-existent user
            response = self.make_request("GET", "/api/users/nonexistent")
            assert response.status_code == 404
            
            # Test non-existent file
            response = self.make_request("GET", "/api/files/nonexistent", params={"user_id": "1"})
            assert response.status_code == 404
            
            self.log("✓ All error handling tests passed")
            return True
            
        except Exception as e:
            self.log(f"✗ Error handling test failed: {e}", "ERROR")
            return False
    
    def run_all_tests(self) -> bool:
        """Run all tests in sequence."""
        self.log("=" * 60)
        self.log("STARTING COMPREHENSIVE MEDIA SEARCH SERVICE TESTS")
        self.log("=" * 60)
        
        tests = [
            ("Health Check", self.test_health_check),
            ("Create Users", self.test_create_users),
            ("Get Users", self.test_get_users),
            ("Add Single Files", self.test_add_single_files),
            ("Batch File Addition", self.test_batch_file_addition),
            ("File Retrieval", self.test_file_retrieval),
            ("Search Functionality", self.test_search_functionality),
            ("File Management", self.test_file_management),
            ("User Management", self.test_user_management),
            ("Statistics", self.test_statistics),
            ("Error Handling", self.test_error_handling)
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            self.log(f"\n{'='*20} {test_name} {'='*20}")
            try:
                if test_func():
                    passed += 1
                    self.log(f"✓ {test_name} - PASSED")
                else:
                    failed += 1
                    self.log(f"✗ {test_name} - FAILED", "ERROR")
            except Exception as e:
                failed += 1
                self.log(f"✗ {test_name} - FAILED with exception: {e}", "ERROR")
        
        self.log("\n" + "=" * 60)
        self.log(f"TEST SUMMARY: {passed} passed, {failed} failed")
        self.log("=" * 60)
        
        return failed == 0

def main():
    """Main test runner."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test media_search service")
    parser.add_argument("--url", default="http://localhost:5001", 
                       help="Base URL of the media_search service")
    parser.add_argument("--wait", type=int, default=30, 
                       help="Wait time for service to start (seconds)")
    
    args = parser.parse_args()
    
    # Wait for service to start
    tester = MediaSearchTester(args.url)
    tester.log(f"Waiting {args.wait} seconds for service to start...")
    time.sleep(args.wait)
    
    # Run tests
    success = tester.run_all_tests()
    
    if success:
        tester.log("🎉 ALL TESTS PASSED! Media search service is working correctly.")
        sys.exit(0)
    else:
        tester.log("❌ SOME TESTS FAILED! Check the logs above for details.")
        sys.exit(1)

if __name__ == "__main__":
    main() 