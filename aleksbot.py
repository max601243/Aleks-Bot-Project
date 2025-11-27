import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageGrab
import pytesseract
import re
from statistics import mean, median
from collections import Counter

from sympy import simplify, solve, expand, factor
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
)

# Permite cosas como (5y + 3z)(y - 7z) sin poner '*'
TRANSFORMATIONS = standard_transformations + (implicit_multiplication_application,)

# ===========================
# CONFIG TESSERACT
# ===========================
# Cambia la ruta si tienes Tesseract instalado en otro sitio
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ===========================
# CORRECCIÓN BÁSICA DE OCR
# ===========================
def corregir_errores_ocr(texto: str) -> str:
    """
    Corrige errores típicos de OCR en contexto matemático:
    - S delante de una variable -> 5 (Sy -> 5y, (Sy -> (5y)
    - l / I delante de dígitos -> 1 (l0 -> 10, I2 -> 12)
    - O / o delante de dígitos -> 0 (O2 -> 02)
    No puede inventar números que el OCR no haya leído.
    """

    # S al inicio de palabra o después de espacio -> 5
    texto = re.sub(r'(?<!\S)S(?=\s*[a-zA-Z0-9])', '5', texto)
    # S después de "(" -> 5
    texto = re.sub(r'\(S(?=\s*[a-zA-Z0-9])', '(5', texto)

    # l o I delante de dígito -> 1
    texto = re.sub(r'(?<!\S)[lI](?=\s*\d)', '1', texto)
    texto = re.sub(r'\([lI](?=\s*\d)', '(1', texto)

    # O u o delante de dígito -> 0
    texto = re.sub(r'(?<!\S)[Oo](?=\s*\d)', '0', texto)
    texto = re.sub(r'\([Oo](?=\s*\d)', '(0', texto)

    return texto

# ===========================
# LIMPIEZA / NORMALIZACIÓN
# ===========================
def normalizar_unicode(texto: str) -> str:
    texto = texto.replace("−", "-").replace("–", "-").replace("—", "-")
    texto = texto.replace("÷", "/")
    texto = texto.replace("^", "**")
    return texto

def limpiar_expresion(texto: str) -> str:
    texto = corregir_errores_ocr(texto)
    texto = normalizar_unicode(texto)
    # dejamos números, letras, operadores, paréntesis, punto y '='
    texto = re.sub(r"[^0-9a-zA-Z+\-*/().= ]", "", texto)
    return texto.strip()

# ===========================
# FORMATO BONITO (5y^2, 32yz, etc.)
# ===========================
def pretty_expr(expr_str) -> str:
    """
    Pasa de:
      5*y**2 - 32*y*z - 21*z**2
    a:
      5y^2 - 32yz - 21z^2
    """
    s = str(expr_str)

    # ** -> ^
    s = s.replace("**", "^")

    # 5*y -> 5y
    s = re.sub(r'(\d)\*([a-zA-Z])', r'\1\2', s)
    # y*z -> yz
    s = re.sub(r'([a-zA-Z])\*([a-zA-Z])', r'\1\2', s)
    # a*( -> a(
    s = re.sub(r'([a-zA-Z0-9])\*\(', r'\1(', s)
    # )*x -> )x
    s = re.sub(r'\)\*([a-zA-Z0-9])', r')\1', s)

    # limpiar espacios dobles
    s = re.sub(r"\s+", " ", s)
    return s.strip()

# ===========================
# NÚMEROS PARA ESTADÍSTICA
# ===========================
def extraer_numeros(texto: str):
    nums = re.findall(r"-?\d+", texto)
    return list(map(int, nums))

def calcular_moda(nums):
    freq = Counter(nums)
    max_f = max(freq.values())
    modas = [n for n, v in freq.items() if v == max_f]
    return modas, max_f

# ===========================
# BUSCAR LÍNEA CON EXPRESIÓN
# ===========================
def encontrar_linea_matematica(texto: str) -> str:
    texto = corregir_errores_ocr(texto)
    lineas = [l.strip() for l in texto.splitlines() if l.strip()]
    candidatas = []

    for l in lineas:
        # línea con números y operadores
        if re.search(r"[0-9]", l) and re.search(r"[+\-*/=()]", l):
            candidatas.append(l)

    if candidatas:
        return candidatas[-1]

    return lineas[-1] if lineas else ""

# ===========================
# INTÉRPRETE "MINI-GPT"
# ===========================
def detectar_accion(texto: str) -> str | None:
    low = texto.lower()

    # prioridad: factorizar > multiplicar/expandir > simplificar
    if "factorizar" in low or "factores" in low or "factorice" in low:
        return "factor"

    if (
        "multiplicar" in low
        or "expanda" in low
        or "expandir" in low
        or "reescribir sin paréntesis" in low
        or "reescriba sin paréntesis" in low
    ):
        return "expand"

    if "simplificar" in low or "simplifique" in low:
        return "simplify"

    return None

def interpretar_problema(texto: str) -> str:
    low = texto.lower()

    # -------- ESTADÍSTICA --------
    if "moda" in low:
        nums = extraer_numeros(texto)
        if not nums:
            return "No encontré números para calcular la moda."
        m, f = calcular_moda(nums)
        return f"""Problema: MODA
Datos: {nums}
Moda(s): {m}
Frecuencia: {f}
"""

    if "media" in low or "promedio" in low:
        nums = extraer_numeros(texto)
        if not nums:
            return "No encontré números para calcular la media."
        return f"""Problema: MEDIA
Datos: {nums}
Media: {mean(nums)}
"""

    if "mediana" in low:
        nums = extraer_numeros(texto)
        if not nums:
            return "No encontré números para calcular la mediana."
        return f"""Problema: MEDIANA
Datos: {nums}
Mediana: {median(nums)}
"""

    if "rango" in low:
        nums = extraer_numeros(texto)
        if not nums:
            return "No encontré números para calcular el rango."
        return f"""Problema: RANGO
Datos: {nums}
Rango: {max(nums) - min(nums)}
"""

    # -------- EXPRESIÓN / ECUACIÓN --------
    linea = encontrar_linea_matematica(texto)
    if not linea:
        return "No pude encontrar una expresión matemática clara en el texto."

    accion = detectar_accion(texto)  # expand / simplify / factor / None
    return explicar_expresion(linea, accion)

# ===========================
# MATEMÁTICAS (EXPRESIONES / ECUACIONES)
# ===========================
def explicar_expresion(exp: str, accion: str | None = None) -> str:
    original = exp
    exp = limpiar_expresion(exp)

    try:
        # ECUACIÓN
        if "=" in exp:
            izq_s, der_s = exp.split("=", 1)
            izq = parse_expr(izq_s, transformations=TRANSFORMATIONS)
            der = parse_expr(der_s, transformations=TRANSFORMATIONS)

            ec = izq - der
            simbolos = list(ec.free_symbols)
            var = simbolos[0] if simbolos else None
            sol = solve(ec, var) if var is not None else []

            pretty_ec = pretty_expr(ec)

            respuesta_final = f"{pretty_ec} = 0"

            return f"""Respuesta final: {respuesta_final}

Ecuación detectada:
{original}

Forma interna:
{ec} = 0

Forma bonita:
{pretty_ec} = 0

Variable: {var}

Solución(es): {sol}
"""

        # EXPRESIÓN
        else:
            parsed = parse_expr(exp, transformations=TRANSFORMATIONS)
            simplified = simplify(parsed)
            expanded = expand(parsed)
            factored = factor(parsed)

            pretty_simpl = pretty_expr(simplified)
            pretty_exp = pretty_expr(expanded)
            pretty_fact = pretty_expr(factored)

            # Escoger respuesta final según acción
            if accion == "expand":
                respuesta_final = pretty_exp
            elif accion == "factor":
                respuesta_final = pretty_fact
            elif accion == "simplify":
                respuesta_final = pretty_simpl
            else:
                # por defecto: simplificada
                respuesta_final = pretty_simpl

            return f"""Respuesta final: {respuesta_final}

Expresión detectada:
{original}

Interpretación interna:
{parsed}

Simplificada (forma interna):
{simplified}

Simplificada (bonita):
{pretty_simpl}

Expandida (forma interna):
{expanded}

Expandida (bonita):
{pretty_exp}

Factorizada (forma interna):
{factored}

Factorizada (bonita):
{pretty_fact}
"""

    except Exception as e:
        return f"""No pude interpretar la expresión.
Expresión original: {original}
Expresión limpiada: {exp}
Error: {e}
"""

# ===========================
# OCR
# ===========================
def leer_imagen(ruta: str) -> str:
    img = Image.open(ruta)
    return pytesseract.image_to_string(img, lang="spa+eng")

def pegar_imagen_desde_clipboard():
    try:
        img = ImageGrab.grabclipboard()
        if img is None:
            return None
        return pytesseract.image_to_string(img, lang="spa+eng")
    except Exception:
        return None

# ===========================
# GUI
# ===========================
def mostrar_ayuda():
    mensaje = (
        "Cómo usar AleksBot:\n\n"
        "1. Para reconocer una imagen desde el portapapeles:\n"
        "   - Toma una captura de pantalla (por ejemplo con la tecla Impr Pant o una herramienta de recorte).\n"
        "   - Copia esa imagen.\n"
        "   - En AleksBot, haz clic en 'Pegar imagen'.\n\n"
        "2. Otra forma es guardar la captura como archivo (PNG, JPG, etc.):\n"
        "   - Guarda la captura en tus archivos.\n"
        "   - En AleksBot, haz clic en 'Cargar imagen' y selecciona el archivo correcto.\n\n"
        "3. Para solucionar un ejercicio y explicarlo:\n"
        "   - Asegúrate de que el texto del ejercicio esté en el cuadro superior.\n"
        "   - Haz clic en el botón 'Explicar'.\n\n"
        "4. Verifica la información que el programa leyó de la imagen:\n"
        "   - Si ves signos, números o expresiones mal leídas,\n"
        "     haz clic en el cuadro de texto y corrige manualmente lo que esté mal.\n"
        "   - Luego vuelve a presionar 'Explicar'.\n"
    )
    messagebox.showinfo("Ayuda - AleksBot Early Access", mensaje)

def cargar_imagen():
    ruta = filedialog.askopenfilename(
        title="Selecciona imagen",
        filetypes=[("Imágenes", "*.png;*.jpg;*.jpeg;*.bmp")]
    )
    if ruta:
        texto = leer_imagen(ruta)
        cuadro_texto.delete("1.0", tk.END)
        cuadro_texto.insert(tk.END, texto)

def pegar_imagen():
    texto = pegar_imagen_desde_clipboard()
    if texto is None:
        messagebox.showinfo("Error", "No hay imagen en el portapapeles.")
        return
    cuadro_texto.delete("1.0", tk.END)
    cuadro_texto.insert(tk.END, texto)

def ejecutar():
    contenido = cuadro_texto.get("1.0", tk.END).strip()
    if not contenido:
        messagebox.showinfo("Error", "No hay texto para analizar.")
        return
    resultado = interpretar_problema(contenido)
    salida.delete("1.0", tk.END)
    salida.insert(tk.END, resultado)

# ===========================
# VENTANA
# ===========================
ventana = tk.Tk()
ventana.title("AleksBot Early Access v1.0.10")
ventana.geometry("800x560")
ventana.attributes("-topmost", True)

frame = tk.Frame(ventana)
frame.pack(pady=10)

# Botón de ayuda (?)
btn_help = tk.Button(frame, text="?", width=3, command=mostrar_ayuda)
btn_help.pack(side="left", padx=(5, 15))

btn1 = tk.Button(frame, text="Cargar imagen", command=cargar_imagen)
btn1.pack(side="left", padx=5)

btn2 = tk.Button(frame, text="Pegar imagen", command=pegar_imagen)
btn2.pack(side="left", padx=5)

btn3 = tk.Button(frame, text="Explicar", command=ejecutar)
btn3.pack(side="left", padx=5)

# Cuadro de texto con SCROLL (entrada)
frame_entrada = tk.Frame(ventana)
frame_entrada.pack(fill="both", expand=True, padx=10, pady=(5, 5))

scroll_entrada = tk.Scrollbar(frame_entrada, orient="vertical")
scroll_entrada.pack(side="right", fill="y")

cuadro_texto = tk.Text(
    frame_entrada,
    height=7,
    wrap="word",
    yscrollcommand=scroll_entrada.set
)
cuadro_texto.pack(side="left", fill="both", expand=True)

scroll_entrada.config(command=cuadro_texto.yview)

# Cuadro de salida con SCROLL
frame_salida = tk.Frame(ventana)
frame_salida.pack(fill="both", expand=True, padx=10, pady=(5, 10))

scroll_salida = tk.Scrollbar(frame_salida, orient="vertical")
scroll_salida.pack(side="right", fill="y")

salida = tk.Text(
    frame_salida,
    height=12,
    wrap="word",
    yscrollcommand=scroll_salida.set
)
salida.pack(side="left", fill="both", expand=True)

scroll_salida.config(command=salida.yview)

ventana.mainloop()




