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
    analysis: str = Field(description="Detailed analysis of the health metric based on self-reports")
    trend: str = Field(description="Observed trend over time (improving/stable/declining)")
    score: int = Field(description="Numerical assessment (1-10) of the current status", ge=1, le=10)
    recommendations: str = Field(description="Suggested actions or recommendations based on the analysis")

class HealthReport(BaseModel):
    general_health: HealthMetric = Field(description="Overall health status and general wellbeing")
    sleep_quality: HealthMetric = Field(description="Sleep patterns and quality analysis")
    physical_activity: HealthMetric = Field(description="Exercise and physical activity assessment")
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
            url = f"http://{base_url}/users/{user_id}/logs/fromIA"

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
        metric_template = """You are a healthcare analyst evaluating {metric_name} from patient self-reports.
        Analyze the provided reports:
        {reports}
        Produce your analysis in the following structure:
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
        prompt_template = """Given the following individual metric analyses, create a comprehensive health report.
        Ensure all analyses are properly integrated and maintain their original structure.

        Individual analyses:
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
                analysis=f"Error analyzing {metric_name}",
                trend="unknown",
                score=5,
                recommendations="Please consult a healthcare provider for proper evaluation"
            )

    def generate_comprehensive_report(self, user_id: int, start_date: str, end_date: str = None) -> HealthReport:
        """Generate a comprehensive health analysis report"""
        reports = self.get_patient_reports(user_id, start_date, end_date)

        # First chain: Analyze individual metrics
        metric_analyses = {
            "general_health": self.analyze_metric("general health", reports).dict(),
            "sleep_quality": self.analyze_metric("sleep quality", reports).dict(),
            "physical_activity": self.analyze_metric("physical activity", reports).dict(),
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
    formatted = "COMPREHENSIVE HEALTH ANALYSIS REPORT\n\n"
    pdf = PDFReport()

    for field_name, field_value in report:
        pdf.add_page()
        formatted += f"=== {field_name.replace('_', ' ').title()} ===\n"
        pdf.chapter_title(field_name.replace('_', ' ').title())

        formatted += f"Current Score: {field_value.score}/10\n"
        pdf.chapter_body(f"Current Score: {field_value.score}/10")

        formatted += f"Trend: {field_value.trend}\n\n"
        pdf.chapter_body(f"Trend: {field_value.trend}")

        formatted += f"Analysis:\n{field_value.analysis}\n\n"
        pdf.chapter_body(f"Analysis:\n{field_value.analysis}")

        formatted += f"Recommendations:\n{field_value.recommendations}\n\n"
        pdf.chapter_body(f"Recommendations:\n{field_value.recommendations}")
        formatted += "-" * 80 + "\n\n"
    
    output_file = "health_analysis_report_ia.pdf"
    pdf.output(output_file)

    return formatted

# Crear la clase para el PDF
class PDFReport(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 12)
        self.cell(0, 10, 'COMPREHENSIVE HEALTH ANALYSIS REPORT', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
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
        user_id=8,
        start_date="2024-11-24",
        end_date="2024-11-24"
    )
    print(format_report_for_display(report))
