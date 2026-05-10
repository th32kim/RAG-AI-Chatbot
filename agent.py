from dotenv import load_dotenv
load_dotenv()
import os
from typing import Any
from llama_index.retrievers.bedrock import AmazonKnowledgeBasesRetriever
from llama_index.llms.openai import OpenAI
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.tools import QueryEngineTool
from llama_index.core.agent.workflow import ReActAgent
from llama_index.core.llms import ChatMessage, MessageRole

retriever = AmazonKnowledgeBasesRetriever(
        knowledge_base_id=os.getenv("BEDROCK_KNOWLEDGE_BASE_ID"),
        retrieval_config={"vectorSearchConfiguration": {"numberOfResults": 3}},
    )
llm = OpenAI(model=os.getenv("OPENAI_MODEL"))

_knowledge_base_tool = QueryEngineTool.from_defaults(
    query_engine=RetrieverQueryEngine(retriever=retriever),
    name="amazon_knowledge_base",
    description=(
        "A vector database of knowledge about companies and their financial data."
    ),
)

agent = ReActAgent(
    tools=[_knowledge_base_tool],
    llm=llm,
    system_prompt=(
        "You are a helpful AI assistant with access to a vector database of knowledge about companies and their financial data. "
        "When users ask questions about companies or their financial data, "
        "use the available tool to retrieve accurate information. "
        "Always provide clear and concise answers based on the retrieved information."
        "You must use English language for your responses and provide the answer in a concise manner."
    ),
)


def _gradio_content_to_text(content: Any) -> str:
    """Gradio 6+ often sends message content as str or list of {type, text} blocks; LlamaIndex expects plain str."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
            elif isinstance(item, dict) and "text" in item:
                parts.append(str(item["text"]))
        return "\n".join(parts).strip()
    if isinstance(content, dict) and content.get("type") == "text":
        return str(content.get("text", ""))
    return str(content)


async def get_agent_response(message, chat_history):
    messages = []
    for msg in chat_history:
        text = _gradio_content_to_text(msg.get("content"))
        if msg["role"] == "user":
            messages.append(ChatMessage(role=MessageRole.USER, content=text))
        elif msg["role"] == "assistant":
            messages.append(ChatMessage(role=MessageRole.ASSISTANT, content=text))

    user_message = ChatMessage(role=MessageRole.USER, content=_gradio_content_to_text(message))
    
    response = await agent.run(user_message, chat_history=messages)
    return str(response)