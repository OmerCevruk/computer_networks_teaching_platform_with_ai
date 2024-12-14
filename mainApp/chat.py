import ollama
from typing import List, Dict
import asyncio


class OllamaChat:
    def __init__(self, model_name: str = "mistral"):
        """Initialize OllamaChat with specified model."""
        self.model_name = model_name

    async def get_response(self, messages: List[Dict[str, str]], context: str = "") -> str:
        """
        Get response from Ollama model.

        Args:
            messages: List of message dictionaries with 'content' and 'is_user' keys
            context: Additional context string to help guide the model's responses

        Returns:
            str: The model's response
        """
        try:
            # Prepare the context and messages
            prompt = f"""Context: {context}

Previous messages:
{self._format_messages(messages)}

Please provide a helpful explanation focusing on computer networking concepts and addressing any misconceptions."""

            # Get response from Ollama using a synchronous call in an executor
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: ollama.chat(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}]
                )
            )

            return response['message']['content']

        except Exception as e:
            return f"Error: {str(e)}"

    def _format_messages(self, messages: List[Dict[str, str]]) -> str:
        """Format chat messages for the prompt."""
        formatted = []
        for msg in messages:
            role = "User" if msg.get('is_user') else "Assistant"
            content = msg.get('content', '')
            formatted.append(f"{role}: {content}")
        return "\n".join(formatted)
