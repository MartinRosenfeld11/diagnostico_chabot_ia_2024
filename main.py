from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser, JsonOutputParser
from datetime import datetime
import requests
import json


# REQUEST AL BACKEND
def get_patient_reports(self, user_id: int, start_date: str, end_date: str = None):
    """Fetch patient self-reports from the API"""
    headers = {"Authorization": f"{TOKEN}"}

    try:
        if end_date:
            response = requests.get(
                f"{BASE_URL}/users/{user_id}/reports",
                params={"start_date": start_date, "end_date": end_date},
                headers=headers
            )
        else:
            response = requests.get(
                f"{BASE_URL}/users/{user_id}/reports",
                params={"start_date": start_date},
                headers=headers
            )

        return response.json()
    except Exception as e:
        return f"Error fetching reports: {str(e)}"
       





# Constants
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from datetime import datetime
import json
import requests

# Constants
BASE_URL = "https://whx3z4mv39.execute-api.us-east-1.amazonaws.com/api"
TOKEN = "Token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.B5lvXGoLR-79Me0lFaaO-EG3ecq1gEMPL8JhK32pElA"

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
        """Mock example of patient self-reports data"""
        mock_reports = [
            {
                "report_id": "r123",
                "user_id": user_id,
                "date": "2024-03-23",
                "metrics": {
                    "general_health": {
                        "feeling": 7,
                        "energy_level": 6,
                        "symptoms": ["mild headache"],
                        "notes": "Felt generally good today but tired"
                    },
                    "sleep": {
                        "hours": 7.5,
                        "quality": 8,
                        "interruptions": 1
                    },
                    "physical_activity": {
                        "exercise_done": True,
                        "duration": 30,
                        "steps": 8500
                    },
                    "pain": {
                        "level": 3,
                        "locations": ["lower back"]
                    },
                    "mood": {
                        "rating": 7,
                        "stress_level": 4
                    },
                    "treatment_adherence": {
                        "medications_taken": True,
                        "exercises_completed": True
                    }
                }
            }
        ]
        return mock_reports

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

    for field_name, field_value in report:
        formatted += f"=== {field_name.replace('_', ' ').title()} ===\n"
        formatted += f"Current Score: {field_value.score}/10\n"
        formatted += f"Trend: {field_value.trend}\n\n"
        formatted += f"Analysis:\n{field_value.analysis}\n\n"
        formatted += f"Recommendations:\n{field_value.recommendations}\n\n"
        formatted += "-" * 80 + "\n\n"

    return formatted

# Usage example
if __name__ == "__main__":
    analyzer = HealthAnalyzer()
    report = analyzer.generate_comprehensive_report(
        user_id=123,
        start_date="2024-01-01",
        end_date="2024-03-23"
    )
    print(format_report_for_display(report))


