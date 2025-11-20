"""
RecoEngine integration service
Handles communication with the RecoEngine API for churn prediction and nudges
"""

import httpx
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from core.config import settings

logger = logging.getLogger(__name__)

class RecoEngineService:
    """Service for integrating with RecoEngine API"""
    
    def __init__(self):
        self.base_url = settings.RECO_ENGINE_URL
        self.timeout = settings.RECO_ENGINE_TIMEOUT
    
    async def predict_churn(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get churn prediction for a user"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}/predict/{user_id}")
                
                if response.status_code == 200:
                    prediction_data = response.json()
                    logger.info(f"Churn prediction for user {user_id}: {prediction_data.get('churn_probability')}")
                    return prediction_data
                else:
                    logger.warning(f"RecoEngine prediction failed for user {user_id}: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error calling RecoEngine predict API: {e}")
            return None
    
    async def ingest_user_behavior(self, user_id: str, behavior_data: Dict[str, Any]) -> bool:
        """Ingest user behavior data to RecoEngine"""
        try:
            # Add user_id to the behavior data
            behavior_data["user_id"] = user_id
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/ingest/behavior",
                    json=behavior_data
                )
                
                if response.status_code == 200:
                    logger.info(f"Behavior data ingested for user {user_id}")
                    return True
                else:
                    logger.warning(f"Behavior ingestion failed for user {user_id}: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error ingesting behavior data: {e}")
            return False
    
    async def ingest_user_profile(self, user_id: str, profile_data: Dict[str, Any]) -> bool:
        """Ingest user profile data to RecoEngine"""
        try:
            # Add user_id to the profile data
            profile_data["user_id"] = user_id
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/ingest/profile",
                    json=profile_data
                )
                
                if response.status_code == 200:
                    logger.info(f"Profile data ingested for user {user_id}")
                    return True
                else:
                    logger.warning(f"Profile ingestion failed for user {user_id}: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error ingesting profile data: {e}")
            return False
    
    async def ingest_transaction_data(self, user_id: str, transaction_data: Dict[str, Any]) -> bool:
        """Ingest transaction data to RecoEngine"""
        try:
            # Add user_id to the transaction data
            transaction_data["user_id"] = user_id
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/ingest/transactional",
                    json=transaction_data
                )
                
                if response.status_code == 200:
                    logger.info(f"Transaction data ingested for user {user_id}")
                    return True
                else:
                    logger.warning(f"Transaction ingestion failed for user {user_id}: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error ingesting transaction data: {e}")
            return False
    
    async def ingest_realtime_features(self, user_id: str, realtime_data: Dict[str, Any]) -> bool:
        """Ingest real-time session features to RecoEngine"""
        try:
            # Add user_id to the realtime data
            realtime_data["user_id"] = user_id
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/ingest/realtime",
                    json=realtime_data
                )
                
                if response.status_code == 200:
                    logger.info(f"Real-time features ingested for user {user_id}")
                    return True
                else:
                    logger.warning(f"Real-time feature ingestion failed for user {user_id}: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error ingesting real-time features: {e}")
            return False
    
    async def ingest_engagement_features(self, user_id: str, engagement_data: Dict[str, Any]) -> bool:
        """Ingest engagement features to RecoEngine"""
        try:
            # Add user_id to the engagement data
            engagement_data["user_id"] = user_id
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/ingest/engagement",
                    json=engagement_data
                )
                
                if response.status_code == 200:
                    logger.info(f"Engagement features ingested for user {user_id}")
                    return True
                else:
                    logger.warning(f"Engagement feature ingestion failed for user {user_id}: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error ingesting engagement features: {e}")
            return False
    
    async def ingest_support_features(self, user_id: str, support_data: Dict[str, Any]) -> bool:
        """Ingest support features to RecoEngine"""
        try:
            # Add user_id to the support data
            support_data["user_id"] = user_id
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/ingest/support",
                    json=support_data
                )
                
                if response.status_code == 200:
                    logger.info(f"Support features ingested for user {user_id}")
                    return True
                else:
                    logger.warning(f"Support feature ingestion failed for user {user_id}: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error ingesting support features: {e}")
            return False
    
    async def health_check(self) -> bool:
        """Check if RecoEngine is healthy"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
                
        except Exception as e:
            logger.error(f"RecoEngine health check failed: {e}")
            return False

# Global RecoEngine service instance
reco_service = RecoEngineService()
