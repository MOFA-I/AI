from issue_analyzer import client


class IssueAnalyzer:
    """사용자 입력에서 국가/이슈를 추출하고, 관련 외교부 데이터를 모아 현황을 정리한다."""

    def analyze(self, country_name: str) -> dict:
        return {
            "country": country_name,
            "travel_warning": client.get_travel_warning_list(country_name=country_name),
            "country_safety": client.get_country_safety_list(content=country_name),
            "security_environment": client.get_security_environment_list(country_name=country_name),
            "overview_situation": client.get_overview_situation_list(country_name=country_name),
            "entrance_visa": client.get_entrance_visa_list(country_name=country_name),
        }
