# test/test_loaders.py
from app.agents.agent2.loaders.overseas_org_loader import load_overseas_org_by_country, load_org_count_by_country
from app.agents.agent2.loaders.koica_country_support_loader import load_oda_cumulative_by_country, load_oda_yearly_by_country
from app.agents.agent2.loaders.koica_project_list_loader import load_project_list, extract_country_guess_from_name

TEST_COUNTRY = "베트남"

print("=" * 60)
print("[overseas_org]")
print(load_overseas_org_by_country(TEST_COUNTRY))

print("=" * 60)
print("[koica_country_support - 누적]")
print(load_oda_cumulative_by_country(TEST_COUNTRY))

print("=" * 60)
print("[koica_country_support - 연도별]")
print(load_oda_yearly_by_country(TEST_COUNTRY))

print("=" * 60)
print("[koica_project_list - 국가 추정]")
df = extract_country_guess_from_name()
print(df[df["country_guess"] == TEST_COUNTRY][["사업번호", "사업명", "country_guess"]].head())