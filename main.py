from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser, JsonOutputParser
from datetime import datetime
import requests
import json
from dotenv import load_dotenv
import openai
import os
from fpdf import FPDF, XPos, YPos
import re

# Importar el token
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")


# Constants
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from datetime import datetime
import json
import requests


def revert_transformation(response_json):
        estado_map = {0: "muy mal", 1: "mal", 2: "regular", 3: "bien", 4: "muy bien"}
        efectos_adversos_map = {0: "si", 1: "no", "no aplica": "no aplica", None: None}
        medicamentos_SOS_map = {0: "si", 1: "no", "no aplica": "no aplica", None: None}
        emociones_map = {
            0: "rabia",
            1: "frustración",
            2: "tristeza",
            3: "miedo",
            4: "alegría",
            None: None,
        }
        efecto_ejercicios_map = {0: "muy mal", 1: "mal", 2: "regular", 3: "bien", 4: "muy bien"}
        calidad_sueno_map = {0: "muy mal", 1: "mal", 2: "regular", 3: "bien", 4: "muy bien"}

        transformed_logs = []

        for log in response_json.get("logs", []):
            try:
                answers = log.get("answers", [])
                transformed_answers = {}

                transformed_answers["estado_general"] = estado_map.get(answers[0], None)
                transformed_answers["tomo_sus_medicamentos"] = "no" if answers[1] == 1 else "si"
                transformed_answers["efectos_adversos_de_medicamentos"] = efectos_adversos_map.get(answers[2], None)
                transformed_answers["intensidad_dolor_general"] = answers[3]
                transformed_answers["crisis_de_dolor"] = answers[4]
                transformed_answers["medicamentos_SOS"] = medicamentos_SOS_map.get(answers[5], None)
                transformed_answers["gatillante_aumento_de_sintomas"] = answers[6]
                transformed_answers["como_afronto_aumento_de_sintomas"] = answers[7]
                transformed_answers["realizo_ejercicios_recomendados"] = "no" if answers[8] == 1 else "si"
                transformed_answers["efecto_ejercicios"] = efecto_ejercicios_map.get(answers[9], None)
                transformed_answers["horas_de_sueno"] = answers[10]
                transformed_answers["calidad_sueno"] = calidad_sueno_map.get(answers[11], None)
                transformed_answers["nivel_de_fatiga"] = answers[12]
                transformed_answers["emocion_predominante"] = emociones_map.get(answers[13], None)
                transformed_answers["mejora_en_dolor"] = answers[14]
                transformed_answers["malestar_gastrointestinal"] = answers[15]
                transformed_answers["variacion_de_peso"] = answers[16]
                transformed_answers["sensacion_cumplimiento_de_metas"] = answers[17]
                transformed_answers["razon_no_medicamentos"] = answers[18]
                transformed_answers["razon_no_ejercicio"] = answers[19]

                transformed_logs.append({
                    "id": log.get("id"),
                    "log_date": log.get("log_date"),
                    "answers": transformed_answers,
                })
            except Exception as e:
                print(f"Error transformig report answers: {str(e)}")

        return {"logs": transformed_logs}

class HealthMetric(BaseModel):
    analysis: str = Field(description="Análisis detallado de la métrica de salud basado en autoevaluaciones")
    trend: str = Field(description="Tendencia observada a lo largo del tiempo (mejorando/estable/empeorando)")
    score: int = Field(description="Evaluación numérica (1-10) del estado actual", ge=1, le=10)
    recommendations: str = Field(description="Acciones o recomendaciones sugeridas basadas en el análisis")

class HealthReport(BaseModel):
    salud_general: HealthMetric = Field(description="Estado general de salud y bienestar")
    calidad_del_sueño: HealthMetric = Field(description="Análisis de patrones y calidad del sueño")
    actividad_física: HealthMetric = Field(description="Evaluación del ejercicio y la actividad física")
    # pain_levels: HealthMetric = Field(description="Pain intensity and frequency analysis")
    # mood_mental_health: HealthMetric = Field(description="Mood patterns and mental health indicators")
    # adherence: HealthMetric = Field(description="Treatment adherence and consistency in reporting")

# HealthAnalyzer Class
class HealthAnalyzer:
    def __init__(self):
        self.model = ChatOpenAI(model="gpt-4o", temperature=0)

    def get_patient_reports(self, user_id: int, start_date: str, end_date: str = None):
        headers = {"Authorization": os.getenv("JWT_ADMIN_BACKEND_ALIVIAUC")}

        try:
            base_url = os.getenv("BASE_URL")
            url = f"https://{base_url}/users/{user_id}/logs/fromIA"

            params = {"start_date": start_date}
            if end_date:
                params["end_date"] = end_date

            response = requests.get(url, params=params, headers=headers)

            if response.status_code != 200:
                return f"Error: El servidor devolvió el estado {response.status_code}: {response.text}"

            reverted_answers = revert_transformation(response.json())
            return reverted_answers
        except Exception as e:
            return f"Error fetching reports: {str(e)}"

    def create_metric_analysis_chain(self):
        """Create a chain for analyzing a specific health metric"""
        metric_parser = JsonOutputParser(pydantic_object=HealthMetric)
        metric_template = """Eres un analista de salud evaluando {metric_name} a partir de autoevaluaciones de los pacientes.
        Analiza los informes proporcionados:
        {reports}
        Produce tu análisis en la siguiente estructura:
        {format_instructions}
        """
        prompt = PromptTemplate(
            template=metric_template,
            input_variables=["metric_name", "reports"],
            partial_variables={"format_instructions": metric_parser.get_format_instructions()},
        )
        chain = prompt | self.model | metric_parser
        return chain

    def create_report_assembly_chain(self):
        """Create a chain for assembling the final report"""
        report_parser = JsonOutputParser(pydantic_object=HealthReport)
        prompt_template = """Dado el siguiente análisis individual de métricas, crea un informe integral de salud.
        Asegúrate de que todos los análisis estén correctamente integrados y mantengan su estructura original.

        Análisis individuales:
        {metric_analyses}
        {format_instructions}
        """
        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["metric_analyses"],
            partial_variables={"format_instructions": report_parser.get_format_instructions()},
        )
        chain = prompt | self.model | report_parser
        return chain

    def analyze_metric(self, metric_name: str, reports: list) -> HealthMetric:
        """Analyze a specific health metric from the reports"""
        chain = self.create_metric_analysis_chain()
        try:
            result = chain.invoke({
                "metric_name": metric_name,
                "reports": json.dumps(reports, indent=2)
            })
            # Convert result to HealthMetric if it's a dictionary
            if isinstance(result, dict):
                result = HealthMetric(**result)
            return result
        except Exception as e:
            print(f"Error analyzing {metric_name}: {str(e)}")
            return HealthMetric(
                analysis=f"Error analizando {metric_name}",
                trend="unknown",
                score=5,
                recommendations="Porfavor consulta con un profesional de la salud para una evaluación adecuada."
            )

    def generate_comprehensive_report(self, user_id: int, start_date: str, end_date: str = None) -> HealthReport:
        """Generate a comprehensive health analysis report"""
        reports = self.get_patient_reports(user_id, start_date, end_date)

        # First chain: Analyze individual metrics
        metric_analyses = {
            "salud_general": self.analyze_metric("salud general", reports).dict(),
            "calidad_del_sueño": self.analyze_metric("calidad del sueño", reports).dict(),
            "actividad_física": self.analyze_metric("actividad física", reports).dict(),
            # "pain_levels": self.analyze_metric("pain levels", reports).dict(),
            # "mood_mental_health": self.analyze_metric("mood and mental health", reports).dict(),
            # "adherence": self.analyze_metric("treatment adherence", reports).dict()
        }

        # Second chain: Assemble final report
        try:
            assembly_chain = self.create_report_assembly_chain()
            final_report = assembly_chain.invoke({
                "metric_analyses": json.dumps(metric_analyses, indent=2)
            })
            # Convert result to HealthReport if it's a dictionary
            if isinstance(final_report, dict):
                final_report = HealthReport(**final_report)
            return final_report
        except Exception as e:
            print(f"Error assembling final report: {str(e)}")
            return HealthReport(**metric_analyses)

# Function to format the report for display
def format_report_for_display(report: HealthReport) -> str:
    """Format the health report for readable display"""
    formatted = "INFORME INTEGRAL DE ANÁLISIS DE SALUD ALIVIA UC\n\n"
    pdf = PDFReport()

    for field_name, field_value in report:
        pdf.add_page()
        formatted += f"=== {field_name.replace('_', ' ').title()} ===\n"
        pdf.chapter_title(field_name.replace('_', ' ').title())

        formatted += f"Puntaje actual: {field_value.score}/10\n"
        pdf.chapter_body(f"Puntaje actual: {field_value.score}/10")

        formatted += f"Tendencia: {field_value.trend}\n\n"
        pdf.chapter_body(f"Tendencia: {field_value.trend}")

        formatted += f"Análisis:\n{field_value.analysis}\n\n"
        pdf.chapter_body(f"Análisis:\n{field_value.analysis}")

        formatted += f"Recomendaciones:\n{field_value.recommendations}\n\n"
        pdf.chapter_body(f"Recomendaciones:\n{field_value.recommendations}")
        formatted += "-" * 80 + "\n\n"
    
    output_file = "Informe_Integral_Análisis_Salud.pdf"
    pdf.output(output_file)

    return formatted

# Crear la clase para el PDF
class PDFReport(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 12)
        self.cell(0, 10, 'INFORME INTEGRAL DE ANÁLISIS DE SALUD ALIVIA UC', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
        self.ln(10)

    def chapter_title(self, title):
        self.set_font('helvetica', 'B', 14)
        self.cell(0, 10, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        self.ln(5)

    def chapter_body(self, body):
        self.set_font('helvetica', '', 12)
        self.multi_cell(0, 10, body.encode('latin-1', 'replace').decode('latin-1'))
        self.ln()



# Usage example
if __name__ == "__main__":
    analyzer = HealthAnalyzer()
    report = analyzer.generate_comprehensive_report(
        user_id=6,
        start_date="2024-11-24",
        end_date="2024-11-24"
    )
    print(format_report_for_display(report))
