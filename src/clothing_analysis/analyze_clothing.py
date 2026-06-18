import base64
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def analyze_clothing(image_bytes: bytes):
    base64_image = base64.b64encode(image_bytes).decode("utf-8")

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": """
                Você é um analisador de roupas para um aplicativo de moda acessível.

                Analise a imagem e responda SOMENTE JSON com:

                {
                  "isClothing": boolean,
                  "category": string | null,
                  "style": string | null,
                  "pattern": string | null,
                  "confidence": number
                }

                Regras:
                - Se NÃO for roupa, isClothing = false
                - category pode ser:
                  camiseta, camisa, moletom, calça, short, saia, vestido, jaqueta, blazer, sapato, tenis, bolsa
                - style pode ser:
                  casual, social, esportivo, streetwear, elegante, basico
                - pattern descreve estampa:
                  lisa, estampada, listrada, xadrez, logo frontal, etc
                """,
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Analise esta imagem.",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        },
                    },
                ],
            },
        ],
    )

    return response.choices[0].message.content