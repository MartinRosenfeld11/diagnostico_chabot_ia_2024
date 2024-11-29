# Deploy de la Función Lambda `lambdaDiagnostico`

Este documento detalla los pasos realizados para construir, desplegar y probar la función Lambda `lambdaDiagnostico`, que forma parte del análisis de salud utilizando una API Gateway y Docker.

---

## 1. Construcción de la Imagen Docker
### Construcción de la Imagen
Ejecuta el siguiente comando para construir la imagen Docker sin usar caché:

```bash
Copiar código
docker build --no-cache -t health-analyzer-lambda-ia-2 .
```

### Etiquetado de la Imagen
Taggea la imagen construida con el repositorio ECR correspondiente:

```bash
Copiar código
docker tag 07f4351e5697 626045775932.dkr.ecr.us-east-1.amazonaws.com/repo-lambda-diagnostico-ia:latest
```
### Push de la Imagen al Repositorio ECR
Envía la imagen al repositorio de AWS Elastic Container Registry (ECR):

```bash
Copiar código
docker push 626045775932.dkr.ecr.us-east-1.amazonaws.com/repo-lambda-diagnostico-ia:latest
```

## 2. Pruebas Locales
### Levantar el Contenedor Localmente
Para ejecutar la imagen Docker en tu máquina local:

```bash
Copiar código
docker run -p 9000:8080 health-analyzer-lambda-ia-2
```
### Realizar una Prueba Local
Usa el siguiente comando curl para probar la función Lambda:

```bash
Copiar código
curl -X POST "http://localhost:9000/2015-03-31/functions/function/invocations" \
    -d '{"body": "{\"user_id\": 10, \"start_date\": \"2024-11-29\"}"}'
```

## 3. Configuración en AWS
### Elastic Container Registry (ECR)
Se creó un repositorio llamado repo-lambda-diagnostico-ia en ECR para alojar la imagen Docker.

### Función Lambda

Se creó una función Lambda llamada lambdaDiagnostico.
La función utiliza la imagen Docker subida al ECR.
Integración con API Gateway:

La función Lambda se conectó al API Gateway ApiGatewayCapstoneBackend.
La ruta configurada es /diagnosticoPaciente con el método ANY.
Versión de la API Gateway: production.

## 4. Invocación desde Postman
### Endpoint:

```plaintext
Copiar código
https://whx3z4mv39.execute-api.us-east-1.amazonaws.com/production/diagnosticoPaciente
```
### Cuerpo de la Solicitud (JSON):
Envía el siguiente JSON en el body para invocar la función:

```json
Copiar código
{
    "user_id": "10",
    "start_date": "2024-11-20"
    // "end_date": "2024-11-29" opcional
}
```
### Encabezados:
Asegúrate de incluir el encabezado Content-Type:

```plaintext
Copiar código
Content-Type: application/json
```

## Notas Finales
La función genera un PDF basado en los datos del paciente enviados en el cuerpo de la solicitud.
Puedes probar la funcionalidad de descarga usando un navegador o herramientas adicionales si el cliente Postman no permite la descarga automática del archivo.
Este proyecto está configurado para producción y puede manejar solicitudes en tiempo real a través del endpoint de API Gateway.
