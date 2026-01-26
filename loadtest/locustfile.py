"""
Locust load testing configuration for Web Gemini Performance Testbed
IEEE Access Research - Load Testing Script
"""

from locust import HttpUser, task, between
import random
import json

class WebGeminiUser(HttpUser):
    """
    Simulates user behavior for load testing
    """
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    
    def on_start(self):
        """Called when a simulated user starts"""
        # Database has 200k users and 50k products
        # Use a smaller pool of user IDs that repeat to test caching effectively
        # This ensures cache hits during load tests
        self.user_pool = list(range(1, 1001))  # Pool of 1000 users that will repeat
        self.max_product_id = 50000
    
    @task(3)
    def search_products(self):
        """
        Task weight: 3 (most common operation)
        Tests: GET /products?search=...
        """
        search_terms = ['laptop', 'shirt', 'book', 'chair', 'ball', 'phone', 'shoes']
        term = random.choice(search_terms)
        
        # Add pagination for optimized version
        page = random.randint(1, 5)
        self.client.get(
            f"/products?search={term}&page={page}&limit=20",
            name="/products?search=[term]"
        )
    
    @task(2)
    def get_user_dashboard(self):
        """
        Task weight: 2 (common operation)
        Tests: GET /users/:id/dashboard
        """
        user_id = random.choice(self.user_pool)
        self.client.get(
            f"/users/{user_id}/dashboard",
            name="/users/[id]/dashboard"
        )
    
    @task(2)
    def get_recommendations(self):
        """
        Task weight: 2 (common operation, tests caching)
        Tests: GET /recommendations/:userId
        Uses a smaller pool of users to ensure cache hits
        """
        user_id = random.choice(self.user_pool)
        self.client.get(
            f"/recommendations/{user_id}",
            name="/recommendations/[userId]"
        )
    
    @task(1)
    def checkout(self):
        """
        Task weight: 1 (less frequent write operation)
        Tests: POST /checkout
        """
        user_id = random.choice(self.user_pool)
        
        # Create a random cart with 1-5 items
        num_items = random.randint(1, 5)
        items = []
        selected_products = random.sample(range(1, self.max_product_id + 1), num_items)
        
        for product_id in selected_products:
            items.append({
                "productId": product_id,
                "quantity": random.randint(1, 3)
            })
        
        self.client.post(
            "/checkout",
            json={
                "userId": user_id,
                "items": items
            },
            name="/checkout"
        )


# Example usage:
# locust -f loadtest/locustfile.py --host=http://localhost:3000 --users=100 --spawn-rate=10 --run-time=5m
# 
# For baseline testing:
# locust -f loadtest/locustfile.py --host=http://localhost:3000 --users=50 --spawn-rate=5 --run-time=3m
#
# For optimized testing:
# locust -f loadtest/locustfile.py --host=http://localhost:3000 --users=100 --spawn-rate=10 --run-time=3m
#
# Export results:
# locust -f loadtest/locustfile.py --host=http://localhost:3000 --users=100 --spawn-rate=10 --run-time=3m --csv=results/locust

