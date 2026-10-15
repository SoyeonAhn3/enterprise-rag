"""Reproducible v2 annotations; PDF quote validation happens before model calls.

python -m eval.expanded_cases writes the separately versioned 60-question file.
The original questions.json and historical results are never modified.
"""

from copy import deepcopy
import json
from pathlib import Path

from config import DOCUMENTS_DIR, PROJECT_ROOT
from ingest import extract_pages

DATASET_PATH = PROJECT_ROOT / "eval/questions_v2.json"
DOCS = {"P": "01_purchase_process.pdf", "A": "02_approval_budget.pdf",
        "S": "03_it_security.pdf", "C": "04_contract_settlement.pdf"}

# Short, contiguous excerpts retain the relevant rule, boundary and qualifier.
REFERENCES = {
    "authority": ("A", 1, "100만원 이하 팀장 공급가액 100만원 100만원 초과 ~ 500만원 이하 부서장 공급가액 180만원 500만원 초과 ~ 2,000만원 이하 재무책임자(CFO) 공급가액 720만원 2,000만원 초과 대표이사(CEO) 공급가액 2,300만원"),
    "total": ("A", 1, "공급가액 총액(VAT 제외)을 사용하며, 운송·설치비 등 구매에 필수적인 비용이 계약에 포함되면 합산한다."),
    "subscription": ("A", 1, "월 구독처럼 주기적으로 지급하는 계약은 최초 약정한 총 계약기간 비용으로 판단한다."),
    "quote_high": ("P", 2, "300만원 이상 서로 다른 공급업체의 유효 견적 2부 이상을 원칙으로 비교"),
    "quote_low": ("P", 2, "300만원 미만 비교견적 의무는 없지만 금액의 합리성 검토와 견적 1부는 필요"),
    "sole": ("P", 2, "단독 공급 불가피 독점 제품·기존 시스템 호환 등 사유서와 구매운영팀 승인 기록"),
    "budget": ("A", 2, "공급가액 500만원 초과 금액별 결재 전에 재무팀의 예산 사전검토 필수 예산 미편성 또는 잔여예산 부족 금액과 무관하게 재무팀 예산 사전검토 필수 예산 내 500만원 이하 예산코드 및 잔여예산 확인 후 정상 결재"),
    "aggregate": ("A", 2, "같은 공급업체와 동일한 구매 목적을 가진 거래를 30일 이내 여러 번 요청하면 합산 공급가액을 기준으로 결재 구간과 비교견적 의무를 판단한다."),
    "legal": ("C", 1, "다음 중 하나라도 해당하면 계약 체결 전에 법무지원팀 사전검토를 받아야 한다. 조건 적용 예시 공급가액 500만원 이상 일시불 500만원 이상의 소프트웨어 계약 계약기간 12개월 이상 소액이더라도 1년 이상 유지보수·구독 계약 고객·직원 개인정보의 처리 위탁 금액이나 계약기간과 관계없이 법무 검토 및 DPA 검토"),
    "security": ("S", 1, "가온비즈에서 회사 업무용으로 구매하는 노트북·데스크톱·서버·네트워크 장비, 신규 유료 SaaS, 회사 명의의 외부 IT 서비스 계약은 금액과 관계없이 발주·계약 전에 정보보안팀 검토를 받아야 한다."),
    "free_security": ("S", 1, "무료 SaaS라도 고객정보·임직원 개인정보·회사 내부자료를 입력하거나 저장하려는 경우에는 무료 체험 시작 전 사전 보안검토가 필요하다."),
    "inspect": ("P", 3, "제품 또는 서비스가 제공되면 요청 부서는 납품·완료 사실을 확인하고, 수령 후 3영업일 이내에 검수 결과를 등록한다."),
    "asset": ("S", 3, "회사 업무용 노트북·모니터·데스크톱 등 자산관리 대상 장비는 구매 요청 부서가 검수 결과를 등록한 뒤, IT지원팀이 검수 완료일부터 5영업일 이내에 자산번호를 부여한다."),
    "emergency": ("P", 3, "이 경우 팀장에게 우선 연락하고 이메일 또는 업무시스템에 임시 승인 흔적을 남긴다. 요청 부서는 1영업일 이내에 정식 구매요청서를 등록해야 한다."),
    "emergency_approval": ("A", 3, "긴급 구매도 상위 결재권자의 승인을 원칙적으로 면제하지 않는다."),
    "small_request": ("P", 3, "50만원 비품도 구매요청이 필요한가요? 필요하다. 다만 300만원 미만이므로 비교견적 2부 의무는 없다."),
    "payment": ("C", 3, "정기 지급 예정일 마감일까지 서류가 완비된 건은 해당 월 25일 지급 예정 마감 이후 접수 다음 월 지급 회차로 이월될 수 있음 지급 예정일은 서류의 적정성·계약조건·금융기관 운영 상황에 따라 변경될 수 있다."),
    "request_fields": ("P", 2, "모든 구매 요청에는 요청자, 소속 부서, 필요 사유, 품목·수량, 희망 납기, 공급가액, 예산코드, 비용 부담 부서, 공급업체(정해진 경우)를 기록한다. 비교견적 대상인 경우 업체별 견적서도 첨부한다."),
    "security_fields": ("S", 1, "사용 목적 업무 목적, 사용 부서, 예상 사용자 수 제품 / 공급업체 상품명, 제공업체, 도입 방식, 계약기간 데이터 처리할 데이터 분류(공개/내부/개인정보 등), 저장 위치 접근관리 관리자 계정, MFA/SSO 지원, 외부 접속 방식 운영·종료 로그·백업, 계약 종료 시 데이터 삭제/반출 방법"),
    "security_outcomes": ("S", 2, "보안 검토 결과에는 승인, 보완 후 승인, 반려 중 하나와 보완 요구사항을 기록한다."),
    "proxy": ("A", 3, "전결권자 부재 시 위임 결재는 회사 결재시스템에 지정된 대리인만 수행할 수 있다. 구두로 전달한 위임은 인정하지 않는다."),
    "invoice": ("C", 4, "세금계산서를 받으면 즉시 지급되나요? 아니요. 계약조건 충족·검수완료·정산 증빙 확인 후 지급됩니다."),
    "bank": ("C", 3, "공급업체 계좌 변경 시 기존 계좌와 다르다는 사유 및 구매운영팀의 확인 기록이 필요하다."),
    "change": ("C", 4, "계약금액, 기간, 주요 산출물, 개인정보 처리 범위가 변경되면 변경 계약서를 작성한다. 변경 후 계약금액이 상위 결재권자의 구간을 넘는 경우 재결재하며, 법무 검토 조건이 새로 충족되면 법무지원팀의 사전 검토를 받는다."),
    "defect": ("C", 2, "불량·수량 부족·미완료 항목이 발견되면 검수 보류 처리하고 공급업체에 시정 요청을 발송한다. 보류 상태에서는 재무팀이 원칙적으로 대금 지급을 진행하지 않는다."),
    "return": ("C", 4, "검수 전 계약을 취소하거나 반품을 진행할 때는 공급업체의 회수 확인, 위약금 또는 취소수수료, 환급액을 기록한다."),
    "trial_end": ("S", 3, "테스트가 끝나면 시험 계정과 저장 데이터를 정리하고, 유료 전환 시에는 구매·결재 절차를 별도로 진행한다."),
    "low_risk": ("S", 2, "낮음 회사 데이터를 저장하지 않는 단순 장비 도입 2영업일"),
    "duration_qualifier": ("S", 2, "상기 기간은 접수 서류가 완비된 시점부터 계산하는 표준 예상 기간이며, 보완 요청이 있는 경우 늘어날 수 있다. 법적 처리 기한이나 승인 보장을 의미하지 않는다."),
    "settlement_submit": ("C", 3, "정산 서류 제출 검수 완료일부터 5영업일 이내 제출"),
    "emergency_personal": ("S", 3, "장애 대응 등 긴급 상황에서도 외부 서비스로 개인정보를 이전할 때는 정보보안팀의 사전 확인을 받아야 한다. 임시 사용이 허용되더라도 적용 범위와 만료 시점을 기록하고 정상 절차를 보완한다."),
    "software_inspect": ("C", 2, "소프트웨어 라이선스 수·기간·계정 발급 및 기능 확인 사용권 증빙, 테스트 기록"),
}

# id, split, family, category, question, required criteria, evidence keys
CASES = [
 (11,"dev","authority_boundaries","single_document","공급가액이 정확히 500만원인 구매의 최종 결재권자는 누구인가요?",["500만원 이하는 부서장 최종 결재 대상이다. CFO라고 하지 않는다."],["authority"]),
 (12,"dev","authority_boundaries","single_document","VAT 제외 2,000만원 구매는 CFO와 CEO 중 누가 최종 승인하나요?",["정확히 2,000만원은 CFO이고 CEO는 2,000만원 초과부터이다."],["authority"]),
 (13,"dev","authority_boundaries","single_document","공급가액 2,001만원 구매의 최종 결재권자는 누구인가요?",["2,000만원 초과이므로 대표이사(CEO)이다."],["authority"]),
 (14,"dev","quote_thresholds","single_document","공급가액이 정확히 300만원이면 서로 다른 업체의 견적이 몇 부 필요한가요?",["300만원 이상이므로 서로 다른 공급업체 유효 견적 2부 이상이 원칙이다."],["quote_high"]),
 (15,"dev","quote_thresholds","single_document","공급가액 299만원 구매는 비교견적 의무가 없으니 견적서를 아예 받지 않아도 되나요?",["비교견적 의무는 없지만 금액의 합리성 검토와 견적 1부는 필요하다."],["quote_low"]),
 (16,"dev","quote_thresholds","single_document","독점 제품이라 400만원 구매에 견적이 1부뿐입니다. 예외로 진행하려면 어떤 기록이 필요한가요?",["단독 공급 사유서와 구매운영팀 승인 기록이 필요하다. 자동 면제가 아니다."],["sole"]),
 (17,"dev","budget_conditions","single_document","정규 예산과 잔여예산이 충분한 정확히 500만원 구매에도 재무팀 별도 예산 사전검토가 필수인가요?",["예산 내 500만원 이하는 예산코드와 잔여예산 확인 후 정상 결재하며 별도 서면검토가 필수인 것은 아니다."],["budget"]),
 (18,"dev","budget_conditions","single_document","50만원 구매인데 잔여예산이 부족합니다. 재무팀 예산 사전검토를 생략할 수 있나요?",["잔여예산 부족이면 금액과 무관하게 재무팀 예산 사전검토가 필수이다."],["budget"]),
 (19,"dev","budget_conditions","single_document","예산은 충분하지만 공급가액이 550만원입니다. 재무팀 예산 검토는 언제 해야 하나요?",["500만원 초과이므로 금액별 결재 전에 재무팀 예산 사전검토가 필수이다."],["budget"]),
 (20,"dev","aggregation_rule","single_document","같은 공급업체에 같은 목적의 구매를 20일 간격으로 두 번 요청하면 금액을 따로 판단하나요?",["동일 공급업체·동일 목적의 30일 이내 요청은 합산 공급가액으로 결재 구간과 비교견적 의무를 판단한다."],["aggregate"]),
 (21,"dev","legal_or_conditions","single_document","개인정보 처리가 없는 200만원짜리 12개월 계약도 법무 검토를 받아야 하나요?",["계약기간 12개월 이상이라는 조건 하나로 계약 체결 전 법무 사전검토가 필요하다. 금액 조건 동시 충족은 필요 없다."],["legal"]),
 (22,"dev","legal_or_conditions","single_document","개인정보 처리가 없는 공급가액 500만원·6개월 계약은 법무 검토 대상인가요?",["정확히 500만원은 500만원 이상에 해당해 계약 체결 전 법무 사전검토 대상이다. 12개월 조건 동시 충족은 필요 없다."],["legal"]),
 (23,"dev","legal_or_conditions","single_document","직원 개인정보 처리 위탁 계약이 200만원·3개월이면 법무와 DPA 검토를 면제받나요?",["개인정보 처리 위탁 자체가 조건이므로 금액·기간과 관계없이 계약 전 법무 및 DPA 검토가 필요하다."],["legal"]),
 (24,"dev","payment_schedule","single_document","정산 서류를 월 정기 접수 마감 이후 제출해도 같은 달 25일 지급이 보장되나요?",["보장되지 않으며 다음 월 지급 회차로 이월될 수 있다. 반드시 다음 달 지급 확정이라고 하지 않는다."],["payment"]),
 (25,"dev","subscription_legal_approval","multi_document","월 공급가액 60만원인 12개월 SaaS 계약의 계산 금액, 최종 결재권자, 계약 전 법무 검토 여부와 이유를 알려주세요.",["총 계약금액은 720만원이고 CFO 최종 결재 대상이다.","계약 전 법무 검토가 필요하며 500만원 이상 또는 12개월 이상 조건 중 하나 이상을 설명한다. 두 조건 동시 충족이 필수라고 하지 않는다."],["subscription","authority","legal"]),
 (26,"dev","subscription_quotes","multi_document","월 30만원씩 12개월 이용하는 외부 서비스의 구매 총액, 최종 결재권자, 비교견적 부수를 알려주세요.",["총 360만원이며 부서장 최종 결재 대상이다.","서로 다른 업체의 유효 견적 2부 이상이 원칙이다."],["subscription","authority","quote_high"]),
 (27,"dev","aggregation_combined","multi_document","같은 업체에 같은 장비를 20일 간격으로 200만원과 160만원에 구매합니다. 합산 금액, 최종 결재권자, 비교견적 요건은요?",["30일 내 동일 목적·업체이므로 360만원으로 합산하고 부서장 최종 결재를 받는다.","서로 다른 업체 유효 견적 2부 이상이 원칙이다."],["aggregate","authority","quote_high"]),
 (28,"dev","laptop_approval_security","multi_document","공급가액 95만원인 업무용 노트북 1대의 최종 결재권자와 보안검토 시점은요?",["100만원 이하이므로 팀장이다.","금액과 수량에 관계없이 발주 전에 정보보안팀 보안검토를 받아야 한다."],["authority","security"]),
 (29,"dev","approval_legal_boundary","multi_document","개인정보 처리가 없는 공급가액 500만원·6개월 소프트웨어 계약의 최종 결재권자와 법무 검토 필요 여부는요?",["정확히 500만원은 부서장 최종 결재 대상이다.","법무 기준은 500만원 이상이므로 계약 체결 전 법무 검토가 필요하다."],["authority","legal"]),
 (30,"dev","budget_legal_approval","multi_document","예산이 충분한 공급가액 550만원·6개월 외부 용역 계약의 최종 결재권자, 예산 검토, 법무 검토를 알려주세요.",["CFO가 최종 결재권자이다.","500만원 초과이므로 결재 전에 재무팀 예산 사전검토가 필요하다.","500만원 이상이므로 계약 체결 전 법무 사전검토가 필요하다."],["authority","budget","legal"]),
 (31,"dev","inspection_asset","multi_document","업무용 노트북을 수령했습니다. 요청 부서의 검수 등록 기한과 IT지원팀의 자산번호 부여 기한은 각각 언제부터 며칠인가요?",["요청 부서는 수령 후 3영업일 이내 검수 등록한다.","IT지원팀은 검수 완료일부터 5영업일 이내 자산번호를 부여한다. 두 시작점을 혼동하지 않는다."],["inspect","asset"]),
 (32,"dev","personal_security_legal","multi_document","고객정보 처리 위탁이 있는 200만원·3개월 신규 SaaS 계약의 보안검토와 법무·DPA 검토는 필요한가요?",["신규 유료 SaaS는 금액과 관계없이 발주·계약 전 보안검토 대상이다.","개인정보 처리 위탁 때문에 금액·기간과 관계없이 계약 전 법무 및 DPA 검토가 필요하다."],["security","legal"]),
 (33,"dev","emergency_approval_process","multi_document","서비스 중단으로 긴급 구매합니다. 우선 승인 기록, 정식 요청서 등록 기한, 상위 결재 면제 여부를 알려주세요.",["팀장에게 우선 연락하고 이메일 또는 업무시스템에 임시 승인 기록을 남긴다.","1영업일 이내 정식 구매요청서를 등록한다.","긴급 구매도 상위 결재권자 승인을 원칙적으로 면제하지 않는다."],["emergency","emergency_approval"]),
 (34,"dev","small_purchase_combined","multi_document","공급가액 50만원 일반 비품도 구매요청서를 내야 하나요? 최종 결재권자도 알려주세요.",["소액 비품도 구매요청이 필요하다.","50만원은 100만원 이하이므로 팀장이 최종 결재한다."],["small_request","authority"]),
 (35,"dev","unknown_contacts","unanswerable","정보보안팀 담당자의 개인 이메일 주소를 알려주세요.",[],[]),
 (36,"dev","unknown_live_budget","unanswerable","우리 마케팅팀의 올해 현재 잔여예산은 정확히 얼마인가요?",[],[]),
 (37,"dev","unknown_product","unanswerable","규정집에서 지정한 업무용 노트북의 정확한 제조사와 모델명을 알려주세요.",[],[]),
 (38,"dev","unknown_order_status","unanswerable","PO-12345 주문의 현재 배송 상태와 확정 도착 날짜는요?",[],[]),
 (39,"dev","unknown_discipline","unanswerable","보안검토를 생략한 직원의 징계는 감봉 몇 개월인가요?",[],[]),
 (40,"dev","missing_purchase_amount","unanswerable","구매 금액은 아직 모릅니다. 이번 장비 구매의 최종 결재권자를 한 명으로 확정해 주세요.",[],[]),
 (41,"final","request_fields","single_document","구매요청서에 반드시 기록할 항목과 비교견적 대상일 때 추가 첨부할 자료를 알려주세요.",["요청자, 소속 부서, 필요 사유, 품목·수량, 희망 납기, 공급가액, 예산코드, 비용 부담 부서, 정해진 경우 공급업체를 포함한다.","비교견적 대상은 업체별 견적서도 첨부한다."],["request_fields"]),
 (42,"final","security_application","single_document","보안검토 신청에 필요한 정보를 사용 목적, 제품, 데이터, 접근관리, 운영·종료 항목별로 알려주세요.",["업무 목적·사용 부서·예상 사용자 수와 상품명·제공업체·도입 방식·계약기간을 포함한다.","데이터 분류·저장 위치, 관리자 계정·MFA/SSO·외부 접속 방식, 로그·백업·종료 시 데이터 삭제/반출 방법을 포함한다."],["security_fields"]),
 (43,"final","security_outcomes","single_document","정보보안팀이 남기는 보안검토 결과의 종류와 함께 기록할 내용은 무엇인가요?",["승인, 보완 후 승인, 반려 중 하나와 보완 요구사항을 기록한다."],["security_outcomes"]),
 (44,"final","delegated_approval","single_document","전결권자가 부재해서 구두 위임을 받았습니다. 대리 결재할 수 있나요?",["결재시스템에 지정된 대리인만 가능하고 구두 위임은 인정하지 않는다."],["proxy"]),
 (45,"final","invoice_payment","single_document","공급업체 세금계산서가 도착했습니다. 다른 절차 없이 즉시 지급할 수 있나요?",["세금계산서만으로 즉시 지급되지 않으며 계약조건 충족, 검수 완료, 정산 증빙 확인이 필요하다."],["invoice"]),
 (46,"final","bank_change","single_document","공급업체가 입금 계좌를 바꿨다고 합니다. 지급 요청에 어떤 추가 기록이 필요한가요?",["기존 계좌와 다른 사유 및 구매운영팀의 확인 기록이 필요하다."],["bank"]),
 (47,"final","contract_changes","single_document","계약금액이나 기간, 산출물, 개인정보 처리 범위를 변경할 때 문서 작성과 재검토는 어떻게 하나요?",["변경 계약서를 작성한다.","상위 결재권자 구간을 넘으면 재결재하고 법무 검토 조건이 새로 충족되면 사전 법무 검토를 받는다."],["change"]),
 (48,"final","defective_delivery","single_document","납품 물품에 불량과 수량 부족이 있습니다. 검수 처리와 공급업체 요청, 대금 지급은 어떻게 하나요?",["검수 보류하고 공급업체에 시정 요청을 발송한다.","보류 상태에서는 원칙적으로 대금을 지급하지 않는다."],["defect"]),
 (49,"final","returns_records","single_document","검수 전에 반품하거나 계약을 취소할 때 어떤 항목을 기록해야 하나요?",["공급업체 회수 확인, 위약금 또는 취소수수료, 환급액을 기록한다."],["return"]),
 (50,"final","trial_cleanup","single_document","SaaS 무료 테스트 종료 후 계정과 데이터는 어떻게 처리하고, 유료로 바꾸려면 어떤 절차가 필요한가요?",["시험 계정과 저장 데이터를 정리한다.","유료 전환 시 구매·결재 절차를 별도로 진행한다."],["trial_end"]),
 (51,"final","request_bank_combined","multi_document","구매요청서에 적을 예산 관련 두 항목과, 나중에 공급업체 지급 계좌가 바뀌었을 때 필요한 기록을 알려주세요.",["구매요청서에 예산코드와 비용 부담 부서를 기록한다.","계좌 변경 사유 및 구매운영팀 확인 기록이 필요하다."],["request_fields","bank"]),
 (52,"final","two_deadlines","multi_document","회사 데이터를 저장하지 않는 단순 장비의 낮은 위험도 보안검토 예상 기간과, 검수 후 정산 서류 제출 기한을 각각 알려주세요.",["보안검토는 서류 완비 시점부터 2영업일이 표준 예상이며 보완 시 늘어날 수 있다.","정산 서류는 검수 완료일부터 5영업일 이내 제출한다."],["low_risk","duration_qualifier","settlement_submit"]),
 (53,"final","shipping_and_return","multi_document","물품 공급가액 1,950만원에 필수 설치비 100만원이 계약에 포함됩니다. 최종 결재권자와 검수 전 반품 시 남길 기록을 알려주세요.",["필수 설치비를 합산한 2,050만원을 기준으로 CEO 최종 결재이다.","반품 시 공급업체 회수 확인, 위약금 또는 취소수수료, 환급액을 기록한다."],["total","authority","return"]),
 (54,"final","emergency_personal_contract","multi_document","장애 대응으로 외부 업체에 개인정보를 긴급 이전하고 처리 위탁 계약을 맺습니다. 보안 사전 확인과 법무·DPA 검토를 생략해도 되나요?",["긴급 상황도 개인정보 이전 전 정보보안팀 사전 확인이 필요하다.","개인정보 처리 위탁은 금액·기간과 무관하게 계약 전 법무 및 DPA 검토가 필요하다."],["emergency_personal","legal"]),
 (55,"final","software_lifecycle","multi_document","소프트웨어 도입 전 보안검토 신청의 데이터 항목과, 납품 후 소프트웨어 검수 항목·보관 증빙을 알려주세요.",["신청 시 처리 데이터 분류와 저장 위치를 제출한다.","검수는 라이선스 수·기간·계정 발급·기능을 확인하고 사용권 증빙과 테스트 기록을 보관한다."],["security_fields","software_inspect"]),
 (56,"final","contract_extension","multi_document","개인정보 처리가 없는 400만원·8개월 계약을 총액 그대로 12개월로 연장합니다. 변경 문서와 법무 검토, 금액 기준 최종 결재권자는요?",["변경 계약서를 작성하며 기간이 12개월 이상이 되어 사전 법무 검토가 필요하다.","금액 기준 최종 결재권자는 부서장이다. 상위 금액 구간으로 올라갔다고 하지 않는다."],["change","legal","authority"]),
 (57,"final","unknown_internal_url","unanswerable","구매요청을 등록하는 회사 업무시스템의 정확한 접속 URL을 알려주세요.",[],[]),
 (58,"final","unknown_named_approver","unanswerable","현재 CFO의 실명과 휴대전화 번호를 알려주세요.",[],[]),
 (59,"final","unknown_refund_amount","unanswerable","우리 회사가 어제 취소한 계약의 실제 환급액은 얼마인가요?",[],[]),
 (60,"final","partial_known_unknown","unanswerable","장비 수령 후 검수 기한과 우리 팀 담당자의 실명을 모두 알려주세요.",[],[]),
]


def build_dataset() -> list[dict]:
    original = json.loads((PROJECT_ROOT / "eval/questions.json").read_text(encoding="utf-8"))
    families = ["authority_boundaries", "quote_thresholds", "inspection_deadline", "free_security",
                "high_risk_duration", "payment_schedule", "laptop_approval_security",
                "subscription_legal_approval", "unknown_cafeteria", "unknown_travel"]
    questions = deepcopy(original)
    for item, family in zip(questions, families):
        item.update(split="dev", family=family)
        item.pop("answer_keywords", None)
    # V2 closes the historical q08 annotation/rubric gap without rewriting v1.
    d, p, quote = REFERENCES["legal"]
    questions[7]["evidence_groups"].append({"id": "legal_general_rule", "claim": "계약 전 검토와 독립적인 금액/기간/개인정보 조건",
                                         "any_of": [{"document": DOCS[d], "page": p, "quote": quote}]})
    for number, split, family, category, question, criteria, keys in CASES:
        answerable = category != "unanswerable"
        groups = []
        for key in keys:
            doc, page, quote = REFERENCES[key]
            groups.append({"id": key, "claim": key, "any_of": [{"document": DOCS[doc], "page": page, "quote": quote}]})
        criteria = criteria or ["요청한 모든 핵심 정보를 문서로 확정할 수 없으므로 정해진 답변 보류 문구를 반환한다.",
                                "횟수·금액·이름·주소·실제 상태를 추측하거나 관련 없는 근거를 붙이지 않는다."]
        questions.append({"id": f"q{number:02d}", "split": split, "family": family, "category": category,
                          "question": question, "answerable": answerable,
                          "expected_answer": " ".join(criteria), "grading_criteria": criteria, "evidence_groups": groups})
    return questions


def validate_dataset(questions: list[dict], *, documents_dir: Path = DOCUMENTS_DIR):
    if len(questions) != 60 or {q["id"] for q in questions} != {f"q{i:02d}" for i in range(1, 61)}:
        raise ValueError("V2 requires exactly 60 unique questions.")
    pages, _ = extract_pages(documents_dir)
    page_text = {(p.metadata["source_file"], p.metadata["page"]): "".join(p.page_content.split()) for p in pages}
    families = {}
    for split, counts in (("dev", (20, 12, 8)), ("final", (10, 6, 4))):
        subset = [q for q in questions if q["split"] == split]
        if tuple(sum(q["category"] == c for q in subset) for c in ("single_document", "multi_document", "unanswerable")) != counts:
            raise ValueError("Unexpected split/category counts.")
    for q in questions:
        if q["family"] in families and families[q["family"]] != q["split"]:
            raise ValueError("Question family leaks across splits.")
        families[q["family"]] = q["split"]
        if bool(q["evidence_groups"]) != q["answerable"] or not q["grading_criteria"]:
            raise ValueError("Missing reference annotations.")
        for group in q["evidence_groups"]:
            for candidate in group["any_of"]:
                quote = "".join(candidate["quote"].split())
                if not quote or quote not in page_text.get((candidate["document"], candidate["page"]), ""):
                    raise ValueError(f"Quote not in PDF: {q['id']} / {group['id']}")


if __name__ == "__main__":
    dataset = build_dataset()
    validate_dataset(dataset)
    text = json.dumps(dataset, ensure_ascii=False, indent=2) + "\n"
    if DATASET_PATH.exists() and DATASET_PATH.read_text(encoding="utf-8") != text:
        raise SystemExit("Dataset already exists with different content; version it instead of overwriting.")
    DATASET_PATH.write_text(text, encoding="utf-8")
    print(f"Validated {len(dataset)} questions against PDF pages; saved {DATASET_PATH.name}.")
