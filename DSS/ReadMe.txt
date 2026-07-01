# Tạo môi trường ảo tên là venv
python3 -m venv venv

# Kích hoạt venv
source venv/bin/activate


---
LUU Y (ban rut gon de chia se nhom):
- Cac file lien quan truc tiep den logic goi AI/LLM va rule engine da duoc
  thay bang ban PLACEHOLDER (giu nguyen class/function de code khac import
  khong loi, nhung khong co logic that ben trong):
    - llm_router.py, radar_llm.py, rule_engine.py, monitor_agent.py
    - agents/rag_advisor_agent.py, agents/retention_agent.py, agents/seller_coach_agent.py
    - app.py (ham generate_narrator_report)
    - pages/1_AI_Risk_Predictor.py (ham fetch_agent_proposal)
    - pages/2_Churn_Management.py (ham fetch_churn_agent_proposal)
    - pages/3_Seller_Intelligence.py (ham fetch_seller_agent_proposal)
    - pages/4_AI_Strategy_Advisor.py (system_instruction + xu ly chat)
    - ui_utils.py (CSS custom + link Spline scene rieng cho tung trang)

- File "Background looping animation.json" da bi xoa khoi ban release nay
  (khong duoc code nao load/su dung, va la asset UI rieng cua chu repo).
- Thu muc data/ (dataset Olist) va cac file model *.pkl khong duoc dinh kem
  (qua nang, tu chay train_*.py de tao lai neu can).
- File .env that (chua API key) khong duoc dinh kem. Dung .env.example lam mau,
  tu dien key rieng cua ban.
- Ban day du (co logic that) dang duoc chu du an giu rieng.
