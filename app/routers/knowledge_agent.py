from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import sys
import os
from typing import List

# Add the parent directory to the path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    # Try relative imports first (when run as module)
    from .. import models, schemas
    from ..database import get_db
    from ..advisor_agent.knowledge_agent_service import KnowledgeAgentService
except ImportError:
    # Fall back to absolute imports (when run directly)
    from app import models, schemas
    from app.database import get_db
    from app.advisor_agent.knowledge_agent_service import KnowledgeAgentService

router = APIRouter(
    prefix="/knowledge-agent",
    tags=["knowledge agent"],
    responses={404: {"description": "Not found"}},
)

# Global service instance (will be initialized on first use)
_knowledge_agent_service: KnowledgeAgentService = None

async def get_knowledge_agent_service() -> KnowledgeAgentService:
    """Get or create the knowledge agent service instance."""
    global _knowledge_agent_service
    if _knowledge_agent_service is None:
        _knowledge_agent_service = KnowledgeAgentService()
        
        # Initialize with default knowledge files (you can add your PDF files here)
        knowledge_files = []
        
        # Look for knowledge base files in the advisor_agent/knowledge_base directory
        knowledge_base_dir = os.path.join(os.path.dirname(__file__), "..", "advisor_agent", "knowledge_base")
        if os.path.exists(knowledge_base_dir):
            for file in os.listdir(knowledge_base_dir):
                if file.endswith(('.pdf', '.txt', '.docx', '.md', '.html', '.json')):  # Added more supported formats
                    knowledge_files.append(os.path.join(knowledge_base_dir, file))
        
        await _knowledge_agent_service.initialize(knowledge_files=knowledge_files)
    return _knowledge_agent_service


@router.post("/ask", response_model=schemas.KnowledgeAgentResponse)
async def ask_knowledge_agent(
    request: schemas.KnowledgeAgentRequest,
    db: Session = Depends(get_db)
):
    """
    Ask the hypertension knowledge agent a question.
    
    The agent provides evidence-based information about hypertension using:
    - **File search (RAG)** from uploaded medical literature and guidelines
    - **Optional user context** from blood pressure data and profile
    
    **Example questions:**
    - "What are the different stages of hypertension?"
    - "How does exercise affect blood pressure?"
    - "What foods should I avoid with high blood pressure?"
    - "What are the side effects of ACE inhibitors?"
    - "How often should I monitor my blood pressure?"
    
    **Features:**
    - Evidence-based answers from medical literature
    - Friendly, educational tone
    - Optional personalization using user's BP data
    - Source citations when available
    """
    # Verify user exists if user_id is provided
    if request.user_id:
        user = db.query(models.User).filter(models.User.id == request.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
    
    try:
        # Get the knowledge agent service
        service = await get_knowledge_agent_service()
        
        # Ask the question
        result = await service.ask_question(
            question=request.question,
            user_id=request.user_id,
            include_user_context=request.include_user_context
        )
        
        # Return the response
        return schemas.KnowledgeAgentResponse(
            question=request.question,
            answer=result.get("answer", "No response generated"),
            sources=result.get("sources", []),
            user_id=request.user_id,
            agent_id=result.get("agent_id"),
            thread_id=result.get("thread_id"),
            vector_store_id=result.get("vector_store_id"),
            status=result.get("status", "unknown")
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get knowledge agent response: {str(e)}"
        )


@router.get("/ask/{question}")
async def ask_knowledge_agent_simple(
    question: str,
    user_id: int = None,
    include_user_context: bool = False,
    db: Session = Depends(get_db)
):
    """
    Simple GET endpoint to ask the knowledge agent a question.
    
    **Parameters:**
    - question: Your question about hypertension
    - user_id: Optional user ID for personalized context
    - include_user_context: Whether to include user's BP data for context
    
    **Example usage:**
    ```
    GET /knowledge-agent/ask/What%20are%20normal%20blood%20pressure%20ranges?
    GET /knowledge-agent/ask/How%20does%20salt%20affect%20blood%20pressure?user_id=1&include_user_context=true
    ```
    """
    # Create request object
    request = schemas.KnowledgeAgentRequest(
        user_id=user_id,
        question=question,
        include_user_context=include_user_context
    )
    
    # Use the main ask endpoint
    return await ask_knowledge_agent(request, db)


@router.post("/upload-knowledge")
async def upload_knowledge_file(
    file: UploadFile = File(...),
    description: str = "Uploaded knowledge base file",
    auto_add_to_vector_store: bool = True
):
    """
    Upload a new file to the knowledge base.
    
    **Supported formats:** PDF, TXT, DOCX, MD, HTML, JSON
    
    **Parameters:**
    - auto_add_to_vector_store: If True, automatically add the file to the existing vector store
    
    **Note:** If auto_add_to_vector_store is False, restart the service to include the new file.
    """
    # Create knowledge_base directory if it doesn't exist
    knowledge_base_dir = os.path.join(os.path.dirname(__file__), "..", "advisor_agent", "knowledge_base")
    os.makedirs(knowledge_base_dir, exist_ok=True)
    
    # Check file type - expanded to match Azure AI Foundry supported formats
    allowed_extensions = {'.pdf', '.txt', '.docx', '.md', '.html', '.json', '.doc', '.pptx'}
    file_extension = os.path.splitext(file.filename)[1].lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"File type {file_extension} not supported. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Check file size (512MB limit)
    content = await file.read()
    if len(content) > 512 * 1024 * 1024:  # 512MB in bytes
        raise HTTPException(
            status_code=413,
            detail="File too large. Maximum size is 512MB."
        )
    
    try:
        # Save the uploaded file
        file_path = os.path.join(knowledge_base_dir, file.filename)
        
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        response_data = {
            "message": "File uploaded successfully",
            "filename": file.filename,
            "path": file_path,
            "size": len(content),
            "description": description
        }
        
        # Try to add to existing vector store if requested and service is initialized
        if auto_add_to_vector_store:
            try:
                global _knowledge_agent_service
                if _knowledge_agent_service is not None:
                    result = await _knowledge_agent_service.add_files_to_knowledge_base([file_path])
                    if result["status"] == "success":
                        response_data["vector_store_status"] = "added_to_existing"
                        response_data["note"] = "File added to existing knowledge base"
                    else:
                        response_data["vector_store_status"] = "failed_to_add"
                        response_data["note"] = f"File saved but not added to vector store: {result.get('message', 'Unknown error')}"
                else:
                    response_data["vector_store_status"] = "service_not_initialized"
                    response_data["note"] = "File saved. Initialize service to include in knowledge base."
            except Exception as e:
                response_data["vector_store_status"] = "error"
                response_data["note"] = f"File saved but error adding to vector store: {str(e)}"
        else:
            response_data["note"] = "File saved. Restart the knowledge agent service to include this file in the knowledge base"
        
        return response_data
        
    except Exception as e:
        # Clean up file if it was created
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload file: {str(e)}"
        )


@router.get("/status")
async def get_knowledge_agent_status():
    """
    Check the knowledge agent service status and configuration.
    """
    try:
        global _knowledge_agent_service
        if _knowledge_agent_service is None:
            return {
                "status": "not_initialized",
                "message": "Knowledge agent service not yet initialized"
            }
        
        # Count knowledge base files
        knowledge_base_dir = os.path.join(os.path.dirname(__file__), "..", "advisor_agent", "knowledge_base")
        knowledge_files = []
        if os.path.exists(knowledge_base_dir):
            knowledge_files = [f for f in os.listdir(knowledge_base_dir) 
                             if f.endswith(('.pdf', '.txt', '.docx', '.md', '.html', '.json', '.doc', '.pptx'))]
        
        # Get vector store info
        vector_store_info = await _knowledge_agent_service.get_vector_store_info()
        
        return {
            "status": "ready",
            "message": "Knowledge agent service is ready",
            "project_endpoint": _knowledge_agent_service.project_endpoint,
            "toolbox_url": _knowledge_agent_service.toolbox_url,
            "agent_id": _knowledge_agent_service.agent_id,
            "vector_store_info": vector_store_info,
            "uploaded_files": len(_knowledge_agent_service.file_ids),
            "knowledge_base_files": knowledge_files,
            "database_tools": len(_knowledge_agent_service.db_tool_definitions),
            "file_search_tool": len(_knowledge_agent_service.file_search_tool.definitions)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Service status check failed: {str(e)}"
        }


@router.post("/initialize")
async def initialize_knowledge_service():
    """
    Manually initialize or reinitialize the knowledge agent service.
    Useful after uploading new knowledge base files.
    """
    try:
        global _knowledge_agent_service
        
        # Find knowledge files
        knowledge_files = []
        knowledge_base_dir = os.path.join(os.path.dirname(__file__), "..", "advisor_agent", "knowledge_base")
        if os.path.exists(knowledge_base_dir):
            for file in os.listdir(knowledge_base_dir):
                if file.endswith(('.pdf', '.txt', '.docx', '.md', '.html', '.json', '.doc', '.pptx')):
                    knowledge_files.append(os.path.join(knowledge_base_dir, file))
        
        # Clean up existing service
        if _knowledge_agent_service:
            await _knowledge_agent_service.cleanup()
        
        _knowledge_agent_service = KnowledgeAgentService()
        await _knowledge_agent_service.initialize(knowledge_files=knowledge_files)
        
        # Get vector store info for response
        vector_store_info = await _knowledge_agent_service.get_vector_store_info()
        
        return {
            "status": "initialized",
            "message": "Knowledge agent service initialized successfully",
            "knowledge_files": [os.path.basename(f) for f in knowledge_files],
            "agent_id": _knowledge_agent_service.agent_id,
            "vector_store_info": vector_store_info,
            "database_tools": len(_knowledge_agent_service.db_tool_definitions)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize service: {str(e)}"
        )


@router.post("/add-files")
async def add_files_to_knowledge_base(
    files: List[UploadFile] = File(...)
):
    """
    Add multiple files to the existing knowledge base without reinitializing.
    
    **Supported formats:** PDF, TXT, DOCX, MD, HTML, JSON, DOC, PPTX
    
    **Note:** This endpoint adds files to the existing vector store directly.
    """
    global _knowledge_agent_service
    if _knowledge_agent_service is None:
        raise HTTPException(
            status_code=400,
            detail="Knowledge agent service not initialized. Use /initialize first."
        )
    
    # Create knowledge_base directory if it doesn't exist
    knowledge_base_dir = os.path.join(os.path.dirname(__file__), "..", "advisor_agent", "knowledge_base")
    os.makedirs(knowledge_base_dir, exist_ok=True)
    
    allowed_extensions = {'.pdf', '.txt', '.docx', '.md', '.html', '.json', '.doc', '.pptx'}
    uploaded_files = []
    errors = []
    
    for file in files:
        try:
            # Check file type
            file_extension = os.path.splitext(file.filename)[1].lower()
            if file_extension not in allowed_extensions:
                errors.append(f"{file.filename}: Unsupported file type {file_extension}")
                continue
            
            # Check file size
            content = await file.read()
            if len(content) > 512 * 1024 * 1024:  # 512MB
                errors.append(f"{file.filename}: File too large (>512MB)")
                continue
            
            # Save file
            file_path = os.path.join(knowledge_base_dir, file.filename)
            with open(file_path, "wb") as buffer:
                buffer.write(content)
            
            uploaded_files.append(file_path)
            
        except Exception as e:
            errors.append(f"{file.filename}: {str(e)}")
    
    # Add files to vector store
    if uploaded_files:
        try:
            result = await _knowledge_agent_service.add_files_to_knowledge_base(uploaded_files)
            
            return {
                "message": "Files processed",
                "uploaded_files": [os.path.basename(f) for f in uploaded_files],
                "vector_store_result": result,
                "errors": errors,
                "total_uploaded": len(uploaded_files),
                "total_errors": len(errors)
            }
        except Exception as e:
            # Clean up uploaded files if vector store addition failed
            for file_path in uploaded_files:
                try:
                    os.remove(file_path)
                except:
                    pass
            
            raise HTTPException(
                status_code=500,
                detail=f"Failed to add files to vector store: {str(e)}"
            )
    else:
        return {
            "message": "No files were successfully uploaded",
            "errors": errors,
            "total_uploaded": 0,
            "total_errors": len(errors)
        }


@router.delete("/reset")
async def reset_knowledge_service():
    """
    Reset the knowledge agent service.
    
    **Warning:** This will clear the current service instance.
    Call /initialize afterwards to reinitialize with knowledge base files.
    """
    try:
        global _knowledge_agent_service
        if _knowledge_agent_service:
            await _knowledge_agent_service.cleanup()
            _knowledge_agent_service = None
        
        return {
            "status": "reset",
            "message": "Knowledge agent service has been reset. Call /initialize to reinitialize."
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset service: {str(e)}"
        )