# Usar una imagen base compatible con Lambda
FROM public.ecr.aws/lambda/python:3.9

# Copiar los archivos del proyecto
COPY lambda_function.py ./
COPY requirements.txt ./
COPY .env ./

# Instalar las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Configurar el handler de Lambda
CMD ["lambda_function.lambda_handler"]
