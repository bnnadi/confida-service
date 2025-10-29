"""
Question Store Service

Handles persistence of questions to PostgreSQL and synchronization with Qdrant vector database.
"""
from typing import List, Dict, Optional
from sqlalchemy import select
from app.database.models import Question
from app.database.qdrant_config import QdrantConfig
from app.utils.logger import get_logger
from qdrant_client.http.models import PointStruct
from datetime import datetime

logger = get_logger(__name__)


class QuestionStoreService:
    """Service for persisting questions and syncing with Qdrant."""
    
    def __init__(self, db_session):
        """
        Initialize QuestionStoreService.
        
        Args:
            db_session: Database session (sync or async)
        """
        self.db_session = db_session
        self.is_async = hasattr(db_session, 'execute')
        self.qdrant_config = QdrantConfig()
        self.qdrant_client = None
        
    def _get_qdrant_client(self):
        """Get or initialize Qdrant client."""
        if self.qdrant_client is None:
            self.qdrant_client = self.qdrant_config.get_client()
        return self.qdrant_client
    
    async def persist_questions(
        self, 
        questions: List[Dict], 
        session_id: Optional[str] = None
    ) -> List[Question]:
        """
        Persist new questions to PostgreSQL.
        Handles both library questions (with existing IDs) and newly generated ones.
        
        Args:
            questions: List of question dictionaries with structure from AI service
            session_id: Optional session ID for tracking
            
        Returns:
            List of persisted Question objects
        """
        persisted_questions = []
        
        try:
            for q_data in questions:
                # Extract question data
                question_text = q_data.get("text") or q_data.get("question_text", "")
                if not question_text:
                    logger.warning(f"Skipping question with no text: {q_data}")
                    continue
                
                source = q_data.get("source", "newly_generated")
                ai_question_id = q_data.get("question_id")
                
                # Handle library questions with known IDs
                if source == "from_library" and ai_question_id:
                    existing = await self._find_question_by_id(ai_question_id)
                    if existing:
                        logger.info(f"Found library question by ID: {existing.id}")
                        persisted_questions.append(existing)
                        continue
                
                # Fallback: dedup by text
                existing_question = await self._find_existing_question(question_text)
                if existing_question:
                    logger.info(f"Question already exists: {existing_question.id}")
                    persisted_questions.append(existing_question)
                    continue
                
                # Extract metadata
                metadata = q_data.get("metadata", {})
                identifiers = q_data.get("identifiers", {})
                
                # Create new question
                question = Question(
                    question_text=question_text,
                    difficulty_level=metadata.get("difficulty_level") or q_data.get("difficulty") or identifiers.get("difficulty", "medium"),
                    category=metadata.get("category") or q_data.get("category") or identifiers.get("category", "general"),
                    subcategory=metadata.get("subcategory") or q_data.get("subcategory") or identifiers.get("subcategory"),
                    compatible_roles=metadata.get("compatible_roles") or ([identifiers.get("role")] if identifiers.get("role") else None),
                    required_skills=metadata.get("required_skills") or q_data.get("skills"),
                    industry_tags=metadata.get("industry_tags"),
                    question_metadata={
                        **metadata,
                        "identifiers": identifiers,
                        "session_id": session_id,
                        "source": source
                    },
                    ai_service_used="ai-service"
                )
                
                if self.is_async:
                    self.db_session.add(question)
                    await self.db_session.flush()
                else:
                    self.db_session.add(question)
                    self.db_session.flush()
                
                persisted_questions.append(question)
                logger.info(f"Persisted new question: {question.id}")
            
            if self.is_async:
                await self.db_session.commit()
            else:
                self.db_session.commit()
                
            logger.info(f"Persisted {len(persisted_questions)} questions")
            return persisted_questions
            
        except Exception as e:
            logger.error(f"Error persisting questions: {e}")
            if self.is_async:
                await self.db_session.rollback()
            else:
                self.db_session.rollback()
            raise
    
    async def _find_existing_question(self, question_text: str) -> Optional[Question]:
        """Find existing question by text."""
        try:
            if self.is_async:
                result = await self.db_session.execute(
                    select(Question).where(Question.question_text == question_text)
                )
                return result.scalar_one_or_none()
            else:
                return self.db_session.query(Question).filter(
                    Question.question_text == question_text
                ).first()
        except Exception as e:
            logger.warning(f"Error finding existing question: {e}")
            return None
    
    async def _find_question_by_id(self, question_id: str) -> Optional[Question]:
        """Find question by UUID."""
        try:
            from uuid import UUID
            question_uuid = UUID(question_id)
            if self.is_async:
                result = await self.db_session.execute(
                    select(Question).where(Question.id == question_uuid)
                )
                return result.scalar_one_or_none()
            else:
                return self.db_session.query(Question).filter(
                    Question.id == question_uuid
                ).first()
        except ValueError:
            logger.warning(f"Invalid question ID format: {question_id}")
            return None
        except Exception as e:
            logger.warning(f"Failed to find question by ID: {e}")
            return None
    
    async def sync_question_to_vector_store(
        self, 
        question: Question, 
        embedding: Optional[List[float]] = None
    ) -> bool:
        """
        Generate embedding if missing, and upsert to Qdrant.
        
        Args:
            question: Question model instance
            embedding: Optional pre-computed embedding vector
            
        Returns:
            bool: True if sync successful, False otherwise
        """
        try:
            client = self._get_qdrant_client()
            
            # Generate embedding if missing - call ai-service for fallback
            if not embedding:
                logger.warning(f"No embedding found for question {question.id}. Calling ai-service for fallback.")
                embedding = await self._generate_embedding(question.question_text)
                if not embedding:
                    logger.warning(f"Fallback embedding generation failed for question {question.id}")
                    return False
            
            # Prepare metadata
            payload = {
                "question_id": str(question.id),
                "difficulty": question.difficulty_level,
                "category": question.category,
                "subcategory": question.subcategory or "",
                "role": question.compatible_roles[0] if question.compatible_roles else "",
                "skills": question.required_skills or [],
                "created_at": datetime.utcnow().isoformat()
            }
            
            # Upsert to Qdrant
            point = PointStruct(
                id=str(question.id),
                vector=embedding,
                payload=payload
            )
            
            client.upsert(
                collection_name="questions",
                points=[point]
            )
            
            logger.info(f"Synced question {question.id} to Qdrant successfully")
            return True
            
        except Exception as e:
            logger.error(f"Qdrant sync failed for {question.id}: {e}")
            return False
    
    async def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for text using ai-service.
        
        Calls the ai-service embedding endpoint instead of direct OpenAI.
        """
        try:
            import httpx
            from app.config import get_settings
            
            settings = get_settings()
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{settings.AI_SERVICE_URL}/embeddings/generate",
                    json={"text": text}
                )
                if resp.status_code == 200:
                    result = resp.json()
                    return result.get("embedding")
                else:
                    logger.warning(f"AI service returned {resp.status_code} for embedding generation")
                    return None
                
        except Exception as e:
            logger.error(f"Error generating embedding via ai-service: {e}")
            return None
    
    async def persist_and_sync_questions(
        self,
        questions: List[Dict],
        embeddings_dict: Optional[Dict[str, List[float]]] = None,
        session_id: Optional[str] = None
    ) -> List[Question]:
        """
        Persist questions and sync to Qdrant in a pseudo-transaction.
        
        This method handles the complete pipeline:
        1. Persists questions to PostgreSQL
        2. Maps embeddings from AI service question IDs to persisted DB IDs
        3. Syncs each question to Qdrant with its corresponding embedding
        
        Args:
            questions: List of question dictionaries from AI service (with question_id)
            embeddings_dict: Dictionary mapping AI service question_id to embedding vectors
            session_id: Optional session ID
            
        Returns:
            List of persisted Question objects
        """
        persisted = []
        try:
            # Step 1: Persist to PostgreSQL
            persisted = await self.persist_questions(questions, session_id)
            
            # Step 2: Map embeddings from AI service IDs to persisted DB IDs
            embedding_map = {}
            if embeddings_dict:
                for q_data, persisted_q in zip(questions, persisted):
                    ai_id = q_data.get("question_id") or q_data.get("id")
                    db_id = str(persisted_q.id)
                    
                    if ai_id and ai_id in embeddings_dict:
                        embedding_map[db_id] = embeddings_dict[ai_id]
                    elif db_id in embeddings_dict:  # Fallback: direct DB ID match
                        embedding_map[db_id] = embeddings_dict[db_id]
            
            # Step 3: Sync to Qdrant with mapped embeddings
            sync_count = 0
            for q in persisted:
                embedding = embedding_map.get(str(q.id))
                success = await self.sync_question_to_vector_store(q, embedding)
                if success:
                    sync_count += 1
                else:
                    logger.warning(f"Qdrant sync failed for {q.id}, but question persisted to DB")
            
            logger.info(f"Synced {sync_count}/{len(persisted)} questions to Qdrant")
            return persisted
        except Exception as e:
            logger.error(f"Transaction failed during persist_and_sync: {e}")
            if self.is_async:
                await self.db_session.rollback()
            else:
                self.db_session.rollback()
            raise
    
    async def batch_sync_questions(
        self,
        questions: List[Question],
        embeddings_dict: Optional[Dict[str, List[float]]] = None
    ):
        """Batch sync multiple questions to Qdrant."""
        for question in questions:
            embedding = None
            if embeddings_dict:
                embedding = embeddings_dict.get(str(question.id))
            await self.sync_question_to_vector_store(question, embedding)

