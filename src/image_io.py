import io

from PIL import Image, ImageCms, ImageOps, UnidentifiedImageError

# As fotos do iPhone vem em Display P3, um espaco de cor mais amplo que o sRGB.
# OpenCV e PIL ignoram o perfil embutido e leem os numeros como se fossem sRGB,
# o que tira saturacao: a mesma cor tem coordenadas mais proximas do cinza em
# P3. Em 19/10/2026, nas 29 pecas cadastradas pelo app, isso fazia um jeans
# azul-marinho sair Preto e um moletom marrom sair Cinza Escuro. Por isso toda
# imagem passa por aqui antes de qualquer analise.
_SRGB = ImageCms.createProfile("sRGB")


def open_srgb(image_bytes: bytes) -> Image.Image:
    """
    Abre a imagem em RGB no espaco sRGB e na orientacao certa (EXIF).

    Levanta ValueError("Imagem inválida") se os bytes nao forem uma imagem.
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))
        image = ImageOps.exif_transpose(image)
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise ValueError("Imagem inválida")

    icc = image.info.get("icc_profile")

    try:
        image = image.convert("RGB")
    except OSError:
        # Arquivo truncado: o cabecalho abre, mas os pixels nao.
        raise ValueError("Imagem inválida")

    if icc:
        try:
            perfil = ImageCms.ImageCmsProfile(io.BytesIO(icc))
            image = ImageCms.profileToProfile(image, perfil, _SRGB, outputMode="RGB")
        except (ImageCms.PyCMSError, OSError):
            # Perfil corrompido: segue com os numeros como vieram, como antes.
            pass

    return image
