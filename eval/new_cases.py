"""AI-authored v3 scenarios checked against the same four synthetic PDFs.

40 new wordings/combinations: 20 dev, 20 final, 4 per test type in each split.
These share source rules with v2; they are not an external blind benchmark.
No RAG results were inspected to write the questions. Reserve final results
before tuning. Validation checks references, not semantic rubric correctness.

python -m eval.new_cases --write creates questions_v3.json without overwriting.
python -m eval.new_cases checks the saved dataset against this specification.
Neither command initializes retrieval, reads credentials, or calls a model.
"""

import argparse
from copy import deepcopy
import json

from config import DOCUMENTS_DIR, PROJECT_ROOT
from eval.datasets import dataset_summary, read_dataset, reject_overlap, validate_questions
from eval.expanded_cases import DOCS, REFERENCES as V2_REFERENCES

DATASET_PATH = PROJECT_ROOT / "eval/questions_v3.json"
REFERENCES = {
    **V2_REFERENCES,
    "purchase_gate": ("P", 1, "구매 요청과 결재가 완료되기 전에는 발주서 발행·계약 확정·선결제를 진행하지 않는다."),
    "po": ("P", 2, "구매운영팀은 사전검토와 결재가 완료된 건에 한해 발주서(PO)를 발행한다. 모든 발주 건에는 PO 번호를 부여하며, 납품 뒤 검수·정산 단계에서도 같은 번호를 사용한다."),
    "order_change": ("P", 3, "품목·수량·금액·납기 변경 시 원 구매요청서와 발주서의 변경 이력을 남긴다. • 금액 변경으로 상위 전결권자 구간에 들어가면 변경 발주 전에 상위 결재를 다시 받는다."),
    "advance": ("P", 3, "사전 승인 없는 선결제는 원칙적으로 인정하지 않으며 재무팀의 별도 검토가 필요하다."),
    "separate_approval": ("A", 2, "재무팀이 예산을 확인했더라도 최종 구매 승인이 완료된 것은 아니다. 재무팀의 예산 사전검토 결과와 전결권자의 구매 승인 내역은 각각 보관한다."),
    "emergency_budget": ("A", 3, "업무 중단 위험 때문에 우선 처리가 필요한 경우 구매지침(GB-PUR-01)에 따라 팀장 임시 승인을 기록하고, 구매요청서와 최종 결재를 사후에 보완한다. 예산 사전검토 대상인 거래는 재무팀과 즉시 협의한다."),
    "security_gate": ("S", 1, "보안검토는 최종 구매 결재를 대체하지 않는다. 구매요청서는 GB-PUR-01에 따라 등록하고, 결재권자는 GB-APR-02의 공급가액 기준으로 판단한다. 보안 검토 결과가 승인되기 전에는 해당 IT 품목을 발주하거나 회사 데이터를 외부 서비스에 이전하지 않는다."),
    "normal_risk": ("S", 2, "보통 내부 문서를 보관하는 외부 SaaS 3영업일"),
    "high_risk": ("S", 2, "높음 개인정보 처리 또는 외부 관리자 접근 5영업일"),
    "private_account": ("S", 3, "개인 이메일 계정으로 회사 데이터를 업로드해 보안검토를 우회하는 행위는 허용되지 않는다."),
    "standard_contract": ("C", 1, "법무 사전검토가 필요 없더라도 회사 표준 계약서를 사용하고 구매 절차는 준수한다."),
    "contract_fields": ("C", 1, "계약 상대방, 납기, 계약기간, 대금 지급조건, 검수 기준, 유지보수·해지 조건을 명시한다."),
    "service_inspect": ("C", 2, "물품은 납품일, 용역은 계약상 산출물 제출일을 기준으로 요청 부서가 3영업일 이내 검수 결과를 등록한다. 구매운영팀은 발주서(PO)와 검수 내역이 일치하는지 확인한다."),
    "reinspect": ("C", 2, "시정 조치가 완료되면 변경된 산출물을 기준으로 재검수한다. 최초 검수일, 보류 사유, 재검수 완료일, 승인자를 기록한다. 변경된 산출물의 비용·계약기간이 달라지면 계약 변경 절차를 추가 적용한다."),
    "payment_documents": ("C", 3, "재무팀에 지급을 요청할 때에는 유효한 발주서(PO 번호 포함), 해당 시 계약서, 납품서 또는 완료 보고서, 검수확인서, 세금계산서, 공급업체 사업자등록 정보와 계좌 확인 자료를 첨부한다."),
    "payment_hold": ("C", 3, "검수 보류 또는 계약조건 미충족 건은 지급 요청이 접수되어도 보완 완료 전까지 지급하지 않는다."),
    "cutoff": ("C", 3, "월 정기 접수 마감 매월 5일 (휴무일이면 다음 영업일)"),
    "termination": ("C", 4, "완료된 계약을 해지하려면 계약서의 해지조건과 미지급 정산 내역을 먼저 확인한다."),
}

# split, number, family, test_type, question, required/negative criteria, evidence keys
CASES = [
    ("dev", 1, "installation_team_limit", "boundary",
     "비품 공급가액 94만원에 계약상 필수 설치비 6만원이 붙습니다. VAT를 제외하면 결재 기준 총액과 최종 승인자는 어떻게 되나요?",
     ["필수 설치비를 합산한 공급가액은 100만원이다.", "정확히 100만원은 팀장 최종 결재 대상이며 부서장으로 올리지 않는다."],
     ["total", "authority"]),
    ("dev", 2, "transport_budget_limit", "boundary",
     "예산이 충분한 장비의 공급가액은 480만원, 계약에 포함된 필수 운송비는 25만원입니다. 최종 결재권자와 재무팀 검토 순서를 알려주세요.",
     ["운송비를 포함해 505만원으로 계산하며 CFO가 최종 결재한다.", "500만원 초과이므로 예산이 충분해도 금액별 결재 전에 재무팀 예산 사전검토가 필요하다."],
     ["total", "authority", "budget"]),
    ("dev", 3, "subscription_quote_limit", "boundary",
     "월 공급가액 25만원으로 12개월을 약정한 서비스를 구매합니다. 견적 비교는 월액과 총액 중 무엇을 기준으로 하며 원칙적으로 몇 부를 받아야 하나요?",
     ["최초 약정한 전체 기간 금액인 300만원을 기준으로 한다.", "300만원 이상에 해당하므로 서로 다른 공급업체의 유효 견적 2부 이상을 원칙으로 비교한다."],
     ["subscription", "quote_high"]),
    ("dev", 4, "finance_legal_threshold_difference", "boundary",
     "개인정보 위탁이 없는 6개월 소프트웨어 계약의 공급가액이 정확히 500만원이고 정규 예산도 충분합니다. 최종 결재, 별도 예산 사전검토, 법무 사전검토를 구분해 주세요.",
     ["최종 결재권자는 부서장이다.", "예산 내 500만원 이하는 예산코드와 잔여예산 확인 후 정상 결재하며 재무팀 별도 서면검토가 필수인 경우가 아니다.",
      "법무 검토는 500만원 이상부터이므로 계약 체결 전에 필요하다. 예산 검토와 같은 초과 기준으로 처리하지 않는다."],
     ["authority", "budget", "legal"]),
    ("dev", 5, "security_to_order_gate", "composite",
     "90만원짜리 업무용 네트워크 장비의 보안 승인은 받았지만 구매요청과 금액별 결재는 하지 않았습니다. 바로 발주 가능한지, 최종 승인자와 PO 발행 담당을 알려주세요.",
     ["보안 승인만으로 발주할 수 없으며 구매요청과 최종 결재도 완료해야 한다.", "공급가액 90만원의 최종 결재권자는 팀장이다.",
      "사전검토와 결재 완료 후 구매운영팀이 PO를 발행한다."],
     ["security_gate", "purchase_gate", "authority", "po"]),
    ("dev", 6, "order_quantity_approval_change", "composite",
     "팀장 승인을 받은 공급가액 95만원 비품 발주를 수량 변경으로 110만원으로 늘립니다. 변경 이력과 변경 발주 전 추가 결재는 어떻게 해야 하나요?",
     ["원 구매요청서와 발주서에 수량·금액 변경 이력을 남긴다.", "110만원은 부서장 구간이므로 변경 발주 전에 상위 결재권자인 부서장 결재를 다시 받는다."],
     ["order_change", "authority"]),
    ("dev", 7, "saas_four_controls", "composite",
     "월 공급가액 40만원인 신규 유료 SaaS를 15개월 약정합니다. 계산 총액, 최종 승인자, 예산·법무·보안 사전검토를 각각 알려주세요.",
     ["약정 총액 600만원으로 계산하고 CFO가 최종 결재한다.", "500만원 초과이므로 금액별 결재 전에 재무팀 예산 사전검토가 필요하다.",
      "500만원 이상 또는 12개월 이상 조건으로 계약 전 법무 사전검토가 필요하다. 두 조건 동시 충족이 필수라고 하지 않는다.",
      "신규 유료 SaaS는 금액과 관계없이 발주·계약 전에 정보보안팀 검토가 필요하다."],
     ["subscription", "authority", "budget", "legal", "security"]),
    ("dev", 8, "small_non_it_contract", "composite",
     "개인정보 위탁이 없는 비IT 용역을 250만원·6개월로 계약합니다. 법무 사전검토 대상이 아니라면 계약서와 견적도 생략할 수 있나요?",
     ["주어진 금액·기간·개인정보 조건으로는 법무 사전검토 대상이 아니지만 회사 표준 계약서를 사용하고 구매 절차를 준수한다.",
      "300만원 미만이라 비교견적 의무는 없지만 견적 1부와 금액 합리성 검토는 필요하다."],
     ["legal", "standard_contract", "quote_low"]),
    ("dev", 9, "cross_department_aggregation", "exception",
     "두 부서가 같은 업체에 같은 목적의 장비를 20일 간격으로 180만원과 150만원씩 요청합니다. 부서가 다르다는 이유로 따로 결재하고 견적 1부씩만 받을 수 있나요?",
     ["같은 업체·동일 목적의 30일 이내 거래는 요청 부서를 나눠도 합산하므로 총 330만원이다.",
      "최종 결재권자는 부서장이고 서로 다른 업체 유효 견적 2부 이상을 원칙으로 비교한다."],
     ["aggregate", "authority", "quote_high"]),
    ("dev", 10, "urgent_budget_coordination", "exception",
     "서비스 중단 대응으로 공급가액 700만원 긴급 구매를 우선 처리해야 합니다. 임시 승인, 정식 요청서 기한, 최종 승인자, 재무팀과의 협의를 알려주세요.",
     ["팀장에게 우선 연락하고 이메일 또는 업무시스템에 임시 승인 흔적을 남기며 요청 부서는 1영업일 이내 정식 구매요청서를 등록한다.",
      "700만원은 CFO 최종 결재 대상이며 긴급 구매도 상위 승인을 원칙적으로 면제하지 않는다.",
      "예산 사전검토 대상 거래이므로 재무팀과 즉시 협의하고 구매요청서와 최종 결재를 사후 보완한다."],
     ["emergency", "authority", "budget", "emergency_approval", "emergency_budget"]),
    ("dev", 11, "unapproved_personal_advance", "exception",
     "80만원 비품은 팀장 결재 구간이라서 사전 승인 없이 개인카드로 먼저 결제했습니다. 소액이라는 이유로 정상 구매로 인정되는지와 필요한 추가 검토는요?",
     ["80만원은 팀장 결재 구간이지만 사전 승인 없는 선결제는 원칙적으로 인정하지 않는다.", "재무팀의 별도 검토가 필요하며 소액이면 자동 승인·정산된다고 하지 않는다."],
     ["authority", "advance"]),
    ("dev", 12, "sole_supplier_budget_shortfall", "exception",
     "독점 제품 420만원 구매에 견적이 하나뿐이고 잔여예산도 부족합니다. 단독 공급 예외를 받으면 예산 검토까지 생략할 수 있나요?",
     ["단독 공급 사유서와 구매운영팀 승인 기록이 필요하고 예외가 자동 적용되는 것은 아니다.",
      "잔여예산 부족은 금액과 무관하게 재무팀 예산 사전검토 대상이며 단독 공급 예외로 이를 면제하지 않는다."],
     ["sole", "budget"]),
    ("dev", 13, "service_submission_acceptance", "timing",
     "외부 용역의 계약상 산출물이 제출됐습니다. 검수 등록은 누가 언제부터 언제까지 하고, PO와 검수 내역의 일치는 누가 확인하나요?",
     ["요청 부서가 계약상 산출물 제출일을 기준으로 3영업일 이내 검수 결과를 등록한다. 계약 체결일이나 대금 지급일부터 계산하지 않는다.",
      "구매운영팀이 발주서(PO)와 검수 내역의 일치를 확인한다."],
     ["service_inspect"]),
    ("dev", 14, "normal_security_clock", "timing",
     "내부 문서를 보관하는 SaaS의 보안 신청은 월요일에 냈지만 서류는 수요일에 완비됐습니다. 표준 검토 기간은 어느 시점부터 며칠이며 보완 요청이 오면 어떻게 되나요?",
     ["내부 문서를 보관하는 외부 SaaS의 보통 위험도 표준 예상 기간은 3영업일이다.",
      "월요일 최초 신청이 아니라 수요일 서류 완비 시점부터 계산하며 보완 요청 시 늘어날 수 있다. 법적 기한이나 승인 보장이 아니다."],
     ["normal_risk", "duration_qualifier"]),
    ("dev", 15, "settlement_two_clocks", "timing",
     "검수가 끝난 뒤 정산 서류를 내는 5영업일과 매월 5일 마감은 같은 뜻인가요? 각 기준의 시작점과 휴무일 처리를 설명해 주세요.",
     ["정산 서류는 검수 완료일부터 5영업일 이내 제출한다.", "월 정기 접수 마감은 매월 5일이고 그날이 휴무일이면 다음 영업일이다. 두 기준을 동일한 기한으로 설명하지 않는다."],
     ["settlement_submit", "cutoff"]),
    ("dev", 16, "holiday_cutoff_payment", "timing",
     "이번 달 5일은 휴무일이고 6일이 다음 영업일입니다. 적정한 정산 서류를 6일에 모두 접수했다면 정기 지급은 언제 예정되며 확정일인가요?",
     ["마감이 다음 영업일인 6일로 이동하므로 마감 내 완비 건은 해당 월 25일 지급 예정이다.",
      "서류 적정성·계약조건·금융기관 운영 상황 등에 따라 달라질 수 있어 확정 지급일이라고 하지 않는다."],
     ["cutoff", "payment"]),
    ("dev", 17, "unknown_po_history", "unanswerable",
     "PO-2026-184의 실제 발행일과 지난주 승인 완료 시각을 조회해 주세요.", [], []),
    ("dev", 18, "unknown_staff_roster", "unanswerable",
     "IT지원팀의 현재 정원과 이번 주 자산 등록 담당자 근무표를 알려주세요.", [], []),
    ("dev", 19, "unknown_vendor_account", "unanswerable",
     "우리 회사가 거래하는 한빛상사의 현재 실제 입금 계좌번호와 은행명을 알려주세요.", [], []),
    ("dev", 20, "unknown_import_rates", "unanswerable",
     "해외 장비 구매의 품목별 관세율과 오늘 적용할 원화 환산 환율을 알려주세요.", [], []),
    ("final", 1, "contract_legal_only_crossing", "boundary",
     "개인정보 위탁이 없는 6개월 계약을 490만원에서 정확히 500만원으로 변경합니다. 변경 계약서, 법무 사전검토, 금액 구간 상향 재결재를 구분해 주세요.",
     ["금액이 변경되므로 변경 계약서를 작성한다.", "500만원 이상 법무 조건이 새로 충족되므로 사전 법무 검토가 필요하다.",
      "490만원과 500만원 모두 부서장 구간이므로 금액 구간 상향에 따른 CFO 재결재라고 하지 않는다."],
     ["change", "legal", "authority"]),
    ("final", 2, "long_subscription_ceo", "boundary",
     "월 공급가액 160만원의 서비스를 13개월 약정합니다. 최종 결재를 CFO가 하면 되는지와 법무 사전검토가 필요한 이유를 알려주세요.",
     ["총 약정 금액은 2,080만원으로 2,000만원을 초과하므로 CFO가 아닌 CEO 최종 결재 대상이다.",
      "500만원 이상 또는 12개월 이상 조건에 해당하여 계약 전 법무 사전검토가 필요하다. 두 조건이 모두 있어야만 검토한다고 하지 않는다."],
     ["subscription", "authority", "legal"]),
    ("final", 3, "installed_price_quote_boundary", "boundary",
     "비품 가격은 VAT 제외 290만원이며 계약상 필수 설치비가 10만원입니다. 견적 비교 기준과 최종 결재권자는 물품 가격만 보고 정하면 되나요?",
     ["필수 설치비까지 합산한 공급가액 300만원을 기준으로 한다.",
      "300만원 이상이므로 서로 다른 공급업체 유효 견적 2부 이상을 원칙으로 비교하고 최종 결재권자는 부서장이다."],
     ["total", "quote_high", "authority"]),
    ("final", 4, "order_ceo_crossing", "boundary",
     "CFO 결재를 받은 공급가액 2,000만원 계약을 2,001만원으로 바꿉니다. 계약 문서와 변경 발주 전 승인에 어떤 조치가 필요한가요?",
     ["금액 변경 내용을 반영한 변경 계약서를 작성한다.", "2,000만원 초과로 CEO 구간에 들어가므로 변경 발주 전에 CEO 결재를 다시 받는다."],
     ["change", "order_change", "authority"]),
    ("final", 5, "short_personal_data_service", "composite",
     "고객 개인정보를 위탁 처리하는 외부 개발 서비스를 200만원·3개월로 계약합니다. 소액·단기인데도 필요한 법무 조치와 보안 검토의 예상 기간·시작점을 알려주세요.",
     ["개인정보 처리 위탁 자체가 법무 사전검토 및 DPA 검토 조건이므로 계약 전에 필요하다.",
      "회사 명의 외부 IT 서비스는 발주·계약 전 보안 검토 대상이며 개인정보 처리는 높은 위험도 검토 대상이다.",
      "높은 위험도의 표준 예상 기간은 서류 완비 시점부터 5영업일이고 보완 요청 시 늘어날 수 있다. 승인 보장이 아니다."],
     ["legal", "security", "high_risk", "duration_qualifier"]),
    ("final", 6, "license_reinspection_records", "composite",
     "소프트웨어의 계정 발급이 누락돼 검수를 보류했다가 공급업체가 수정했습니다. 소프트웨어 검수 항목·증빙과 재검수 시 남길 이력을 알려주세요.",
     ["라이선스 수·기간·계정 발급·기능을 확인하고 사용권 증빙과 테스트 기록을 보관한다.",
      "시정 완료 후 변경된 산출물을 기준으로 재검수하고 최초 검수일, 보류 사유, 재검수 완료일, 승인자를 기록한다."],
     ["software_inspect", "reinspect"]),
    ("final", 7, "saas_exit_contract_alignment", "composite",
     "새 SaaS의 보안 신청과 계약서를 준비합니다. 보안 신청의 데이터·접근관리·운영 종료 정보와 계약서의 지급·검수·해지 조건에는 무엇을 적어야 하나요?",
     ["보안 신청에 데이터 분류와 저장 위치, 관리자 계정·MFA/SSO 지원·외부 접속 방식, 로그·백업 및 종료 시 데이터 삭제·반출 방법을 포함한다.",
      "계약서에 대금 지급조건, 검수 기준, 유지보수·해지 조건을 명시한다."],
     ["security_fields", "contract_fields"]),
    ("final", 8, "po_bank_payment_chain", "composite",
     "검수와 세금계산서는 준비됐는데 지급 요청에서 PO 자료가 빠졌고 공급업체 계좌도 바뀌었습니다. 어떤 PO 번호를 쓰고 계좌 변경에 어떤 기록을 보완해야 하나요?",
     ["발주 시 부여한 동일 PO 번호를 검수·정산에도 사용하며 PO 번호가 포함된 유효한 발주서를 지급 요청에 첨부한다.",
      "계좌 확인 자료와 함께 기존 계좌와 다른 사유 및 구매운영팀의 확인 기록을 갖춘다. 세금계산서만으로 충분하다고 하지 않는다."],
     ["po", "payment_documents", "bank"]),
    ("final", 9, "urgent_data_transfer_controls", "exception",
     "장애 복구 때문에 외부 서비스에 개인정보를 임시 이전하고 긴급 구매를 진행합니다. 이전 전 확인, 임시 허용 기록, 정식 구매요청서 보완 기한을 알려주세요.",
     ["긴급 상황도 개인정보 이전 전에 정보보안팀 사전 확인을 받아야 한다.",
      "임시 허용 범위와 만료 시점을 기록하고 정상 절차를 보완한다.",
      "팀장에게 우선 연락해 임시 승인 흔적을 남기고 요청 부서는 1영업일 이내 정식 구매요청서를 등록한다."],
     ["emergency_personal", "emergency"]),
    ("final", 10, "trial_exit_paid_transition", "exception",
     "내부자료를 쓰는 무료 체험을 개인 이메일로 시작하고 나중에 유료 전환하려 합니다. 계정 방식으로 보안검토를 생략할 수 있는지와 체험 종료·유료 전환 시 조치를 알려주세요.",
     ["개인 이메일로 보안검토를 우회할 수 없고 내부자료를 입력·저장하는 무료 체험도 시작 전 사전 보안검토가 필요하다.",
      "체험 종료 후 시험 계정과 저장 데이터를 정리하며 유료 전환 때 구매·결재 절차를 별도로 진행한다."],
     ["private_account", "free_security", "trial_end"]),
    ("final", 11, "budget_and_deputy_gate", "exception",
     "350만원 구매의 재무팀 예산 확인은 끝났지만 부서장이 부재합니다. 구두 위임을 받은 동료가 대신 최종 결재해도 되며 어떤 승인 기록을 보관해야 하나요?",
     ["350만원의 금액별 최종 결재권자는 부서장이며 대리 결재는 결재시스템에 지정된 대리인만 할 수 있다. 구두 위임은 인정하지 않는다.",
      "예산 확인이 최종 구매 승인을 대신하지 않으며 재무팀 예산 사전검토 결과와 전결권자 구매 승인 내역을 각각 보관한다."],
     ["authority", "proxy", "separate_approval"]),
    ("final", 12, "defect_duration_change", "exception",
     "개인정보 위탁 없는 200만원·6개월 용역을 검수 보류 중입니다. 지급 서류는 접수했고, 시정 과정에서 기간을 12개월로 늘리기로 했습니다. 지급과 계약 변경·법무 검토는 어떻게 하나요?",
     ["서류가 접수됐어도 검수 보류나 계약조건 미충족은 보완 완료 전까지 지급하지 않는다.",
      "기간 변경을 반영한 변경 계약서를 작성하고 새로 12개월 이상 조건이 충족되므로 사전 법무 검토를 받는다."],
     ["payment_hold", "change", "legal"]),
    ("final", 13, "equipment_three_milestones", "timing",
     "모니터를 수령한 뒤 검수 등록, 자산번호 부여, 정산 서류 제출이 남았습니다. 각 기한의 기준 시점과 검수·자산번호 담당을 구분해 주세요.",
     ["구매 요청 부서는 수령 후 3영업일 이내 검수 결과를 등록한다.",
      "검수 결과 등록 뒤 IT지원팀이 검수 완료일부터 5영업일 이내 자산번호를 부여한다.",
      "정산 서류도 검수 완료일부터 5영업일 이내 제출하며 두 5영업일 기준을 장비 수령일부터 계산하지 않는다."],
     ["inspect", "asset", "settlement_submit"]),
    ("final", 14, "external_admin_review_clock", "timing",
     "개인정보 처리는 없지만 외부 업체가 내부 시스템에 관리자 수준으로 접근합니다. 보통 위험도 3영업일로 보면 되나요? 표준 기간과 계산 시작점을 알려주세요.",
     ["외부 관리자 접근은 높은 위험도에 해당해 표준 예상 기간은 5영업일이며 보통 위험도 3영업일로 확정하지 않는다.",
      "접수 서류가 완비된 시점부터 계산하고 보완 요청 시 늘어날 수 있다. 법적 처리 기한이나 승인 보장을 의미하지 않는다."],
     ["high_risk", "duration_qualifier"]),
    ("final", 15, "late_complete_submission", "timing",
     "이번 달 5일이 영업일인데 정산 증빙이 8일에야 모두 완비돼 접수됐습니다. 이번 달 25일 지급이 보장되나요? 다음 회차도 확정일인가요?",
     ["매월 5일 마감 이후 완비 접수이므로 다음 월 지급 회차로 이월될 수 있으며 이번 달 25일 지급을 보장하지 않는다.",
      "지급 예정일은 서류 적정성·계약조건·금융기관 상황에 따라 달라질 수 있으므로 다음 회차 날짜도 확정 지급일이라고 하지 않는다."],
     ["cutoff", "payment"]),
    ("final", 16, "cancellation_vs_termination", "timing",
     "검수 전에 계약을 취소하는 경우와 이미 완료된 계약을 해지하는 경우를 비교해, 각각 기록하거나 먼저 확인할 사항을 알려주세요.",
     ["검수 전 취소·반품은 공급업체 회수 확인, 위약금 또는 취소수수료, 환급액을 기록한다.",
      "완료된 계약의 해지는 먼저 계약서 해지조건과 미지급 정산 내역을 확인한다. 실제 수수료나 환급 금액을 추측하지 않는다."],
     ["return", "termination"]),
    ("final", 17, "unknown_budget_balance", "unanswerable",
     "예산코드 DEV-42에 오늘 남아 있는 실제 잔여예산은 얼마인가요?", [], []),
    ("final", 18, "unknown_violation_penalty", "unanswerable",
     "보안검토 없이 내부자료를 올린 직원에게 적용되는 사내 징계 등급과 벌금 액수를 알려주세요.", [], []),
    ("final", 19, "unknown_api_pricing", "unanswerable",
     "회사에서 계약한 AI API의 모델별 입력·출력 토큰 단가를 알려주세요.", [], []),
    ("final", 20, "unknown_company_calendar", "unanswerable",
     "회사의 2027년 지정 휴무일 목록과 그 달력을 적용한 2월 정산 접수 마감 날짜를 알려주세요.", [], []),
]


def build_dataset():
    questions = []
    for split, number, family, test_type, wording, required, keys in CASES:
        criteria = required or ["요청한 실제 값·상태·정보를 문서에서 확정할 수 없으므로 정해진 답변 보류 문구를 반환한다.",
                                "없는 정보나 근거를 만들어내지 않고 관련 규정만으로 실제 값을 추측하지 않는다."]
        groups = []
        for key in keys:
            document, page, quote = REFERENCES[key]
            groups.append({"id": key, "claim": quote,
                           "any_of": [{"document": DOCS[document], "page": page, "quote": quote}]})
        documents = {c["document"] for g in groups for c in g["any_of"]}
        category = ("unanswerable" if not keys else "single_document" if len(documents) == 1 else "multi_document")
        questions.append({"id": f"v3_{split[0]}{number:02d}", "split": split, "family": family,
                          "category": category, "test_type": test_type, "question": wording,
                          "answerable": bool(keys), "expected_answer": " ".join(criteria),
                          "grading_criteria": deepcopy(criteria), "evidence_groups": groups})
    return questions


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    questions = build_dataset()
    validate_questions(questions, documents_dir=DOCUMENTS_DIR)
    reject_overlap(questions, read_dataset(PROJECT_ROOT / "eval/questions_v2.json"))
    content = json.dumps(questions, ensure_ascii=False, indent=2) + "\n"
    if args.write and not DATASET_PATH.exists():
        with DATASET_PATH.open("x", encoding="utf-8") as handle:
            handle.write(content)
    if read_dataset(DATASET_PATH) != questions:
        raise ValueError("Saved v3 differs from its specification; version it instead of overwriting.")
    print(json.dumps({"status": "validated_no_calls", **dataset_summary(questions)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
