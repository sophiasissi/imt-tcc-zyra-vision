import base64
import io
import json
import os

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image, UnidentifiedImageError

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def analyze_clothing(image_bytes: bytes):
    try:
        Image.open(io.BytesIO(image_bytes)).verify()
    except UnidentifiedImageError:
        raise ValueError("Imagem inválida")

    base64_image = base64.b64encode(image_bytes).decode("utf-8")

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": """
                Você é um analisador de roupas para um aplicativo de moda acessível.
                A imagem já foi validada como uma peça de roupa.

                Analise a imagem e responda SOMENTE JSON com:

                {
                  "category": string | null,
                  "style": string | null,
                  "pattern": string | null,
                  "fabric": string | null,
                  "occasion": string | null
                }

                Regras:
                - Use sempre adjetivos no masculino (ex: "liso", nunca "lisa"),
                  independentemente do gênero gramatical da peça
                - category pode ser:
                  camiseta, camisa, moletom, calça, short, saia, vestido, jaqueta, blazer, sapato, tenis, bolsa
                - style pode ser:
                  casual, social, esportivo, streetwear, elegante, basico
                - pattern descreve estampa:
                  liso, estampado, listrado, xadrez, logo frontal, etc
                - fabric descreve o material predominante:
                  algodão, jeans, couro, linho, malha, poliéster, lã, seda, veludo, etc
                - occasion pode ser:
                  praia, trabalho, festa, academia, dia-a-dia, casa
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

    content = response.choices[0].message.content

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        raise ValueError("Resposta inválida da IA")
