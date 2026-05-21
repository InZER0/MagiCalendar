import os
import streamlit as st
import google.generativeai as genai
import pandas as pd
import json, smtplib, ssl, io, requests
import time
import threading
import gspread
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# --- [내장 API 키 설정] --- 

GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
TELEGRAM_BOT_TOKEN = st.secrets["TELEGRAM_BOT_TOKEN"]

from google.oauth2.service_account import Credentials

# --- [spread sheet 불러오기] ---
def get_sheets_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=[
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
    )
    return gspread.authorize(creds)
    
# --- [google spread sheet에 알림 보낼 내용 저장] ---
def save_alarm_to_sheets(email, chat_id, event, alarm_dt):
    client = get_sheets_client()
    sheet = client.open_by_key(st.secrets["SHEETS_ID"]).sheet1
    sheet.append_row([
        email,
        chat_id,
        event.get('event'),
        event.get('date'),
        event.get('time'),
        event.get('place'),
        event.get('summary'),
        alarm_dt.strftime('%Y-%m-%d %H:%M'),
        "FALSE"
    ])

import threading

# --- [텔레그램 /myid 명령어 코드 봇 활성화] ---
def run_bot():
    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
            res = requests.get(url, params={"offset": offset, "timeout": 30})
            updates = res.json().get("result", [])
            for update in updates:
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                if not msg:
                    continue
                text = msg.get("text", "")
                chat_id = msg["chat"]["id"]
                if text == "/myid":
                    requests.post(
                        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                        json={
                            "chat_id": chat_id,
                            "text": f"🆔 당신의 Chat ID는:\n`{chat_id}`\n\nMagiCalendar에 입력하세요!",
                            "parse_mode": "Markdown"
                        }
                    )
        except:
            pass
        time.sleep(1)

# 2. 핵심: 앱 전체에서 딱 한 번만 실행되도록 잠금장치 걸기
@st.cache_resource
def start_bot_once():
    # 백그라운드 스레드에서 run_bot을 실행 (메인 웹 화면이 멈추지 않게 함)
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    return "Bot is running globally!"

# 3. 봇 실행 호출
# 사용자가 탭을 10개 열어도, 이 함수는 캐싱 덕분에 최초 1번만 실행됩니다.
start_bot_once()


st.set_page_config(page_title="✨ MagiCalendar", layout="wide")

# --- UI 스타일 ---
st.markdown("""
<style>
    /* 위아래 간격 줄이기 */
    [data-testid='stVerticalBlock'] { gap: 0.1rem; }
    div[data-testid='column'] { padding: 0px !important; }
    /* 입력창 글자 진하게 및 검정색 */
    input { color: #000000 !important; font-weight: bold !important; }
    /* 위젯 크기 최적화 */
    div[data-testid='stNumberInput'] { max-width: 120px; }
    div[data-testid='stDateInput'] { max-width: 160px; }
    .stCheckbox { margin-bottom: -15px; }
</style>
""", unsafe_allow_html=True)

if 'events' not in st.session_state: st.session_state.events = []
if 'metadata' not in st.session_state: st.session_state.metadata = {}
if 'selected_notifications' not in st.session_state: st.session_state.selected_notifications = {}

# --- Sidebar ---

st.sidebar.markdown(
    """
    <h1 style='text-align: center; font-size: 35px; font-weight: bold;adding-left: 5px;'>
        ✨MagiCalendar
    </h1>
    """,
    unsafe_allow_html=True
)

st.sidebar.divider()

st.sidebar.markdown(
    """
    <div style="text-align: center; font-size: 29px; font-weight: bold; margin-bottom: 15px;">
        ⚙️Developers
    </div>
    <div style="text-align: left; font-size: 17px; font-weight: bold; line-height: 2.5; padding-left: 5px;">
        💻첨단융합학부 202670690 홍인영<br>
        🛠️첨단융합학부 202670643 이준성<br>
    <div>
    <div style="text-align: left; font-size: 16px; font-weight: bold; line-height: 2.5; padding-left: 2px;">
        💡첨단IT자율전공 202628176 이혁준
    </div>
    """,
    unsafe_allow_html=True
)

st.sidebar.divider()
with st.sidebar:

    # 1. 사이드바 타이틀 중앙 정렬
    st.markdown(
        """
        <div style="text-align: center; font-size: 12px">
            <h3 style="margin-bottom: 4px;">📢 테스트용 샘플 파일 다운로드</h3>
        </div>
        """, 
        unsafe_allow_html=True
    )
    for _ in range(6): st.write("")
    presentation_data = {
        'Date': [
            '2026-06-04 10:05:04', '2026-06-04 10:05:06', '2026-06-04 10:05:24', 
            '2026-06-04 10:14:32', '2026-06-04 10:15:37', '2026-06-04 10:15:58'
        ],
        'User': ['홍인영', '홍인영', '홍인영', '홍인영', '홍인영', '홍인영'],
        'Message': [
            '길동이 전화번호는 010-1234-5678이야',
            '길동이 메일은 gildong@magicalendar.cloud야'
            'www.pnupcbang.co.kr 사이트에서 회원가입을 미리 해야돼 ',
            '6월 4일 오후 1시 30분에 나랑 길동이랑 pc방에 가서 롤할거야',
            '6월 4일 오후 1시 10분에는 길동이랑 부산밀면 집에서 밀면 먹을거야',
            "6월 4일 오후 2시에는 해운대 CGV에서 '왕과사는남자' 영화를 나 혼자 볼거야",
            '그리고 나는 6월 5일 오전 10시에 일어나야돼'
        ]
    }
    
    sample_df = pd.DataFrame(presentation_data)
    csv_bytes = sample_df.to_csv(index=False).encode('utf-8-sig')

    # 2. 사이드바 내부 공간을 [왼쪽 여백(1), 가운데 버튼(2), 오른쪽 여백(1)] 비율로 쪼개기
    col1, col2, col3 = st.columns([1, 2.8, 1])
    
    # 3. 정중앙인 col2(가운데 칸)에 다운로드 버튼을 쏙 넣기
    with col2:

    # 다운로드 버튼 배치 (위의 CSS 덕분에 자동으로 가운데로 정렬됩니다)
    # 다운로드 버튼 배치 (help 가이드를 물음표 툴팁으로 처리)
        st.download_button(
            label="📥 샘플 다운로드",
            data=csv_bytes,
            file_name="테스트용_샘플.csv",
            mime="text/csv",
            help="직접 테스트해보고 싶으신 분들은 샘플 파일을 다운로드한 후, 메인 화면의 업로드 창에 넣어보세요!"
        )
    st.markdown("---")


# --- gemini 불러오기 및 프롬포트 ---
st.title("✨MagiCalendar : AI 일정 관리")
uploaded_file = st.file_uploader("📂 카카오톡 대화내역 CSV 업로드", type="csv")

if st.button("✨ AI 일정 분석 시작!", type="primary"):
    if uploaded_file:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-3.1-flash-lite')
        df = pd.read_csv(uploaded_file)
        content_str = df.to_string()
        prompt = f"""
아래는 카카오톡 대화 CSV 데이터야.
분석해서 반드시 아래 JSON 구조로만 응답해.
다른 텍스트, 마크다운, 코드블록 절대 금지.
모든 텍스트 값은 반드시 한국어로 작성해.

{{
  "events": [
    {{
      "event": "일정명 (한국어)",
      "date": "YYYY-MM-DD (불명확하면 미정)",
      "time": "HH:MM (불명확하면 미정)",
      "place": "장소 (대화에서 유추 가능하면 반드시 채워넣어, 불명확할 때만 미정)",
      "participants": "참여자 (대화에 등장하는 모든 이름 추출, 없으면 미정)",
      "importance": "높음 또는 보통 또는 낮음",
      "summary": "해당 일정과 관련된 대화 내용을 2~3문장으로 자세히 요약 (한국어)"
    }}
  ],
  "metadata": {{
    "global_summary": "전체 대화를 5줄 이상 자세하게 한국어로 요약",
    "links": ["url1"],
    "phones": ["010-0000-0000"],
    "emails": ["xxx@xxx.com"],
    "keywords": ["중요한 단어만 추출 (일반적인 단어 제외, 고유명사/장소/인물 위주)"]
  }}
}}

데이터:
{content_str[:20000]}
"""
        with st.spinner("AI 분석 중..."):
            response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
            res = json.loads(response.text)
            st.session_state.events = res.get('events', [])
            st.session_state.metadata = res.get('metadata', {})

if st.session_state.events:
    # 섹션 1: 요약
    st.header("💬 AI 대화 요약")
    st.info(st.session_state.metadata.get('global_summary', '요약 정보 없음'))

    # 섹션 2: 일정 목록
    st.header(f"📅 발견된 일정 {len(st.session_state.events)}개")

    # Reset selected_notifications at the start of event display loop
    st.session_state.selected_notifications = {}

    for i, ev in enumerate(st.session_state.events):
        event_key = f"ev_{i}"
        with st.container():
            # 줄 1: 체크박스 + 일정 정보
            col_chk, col_info = st.columns([0.3, 9])
            with col_chk:
                # Initialize checkbox state if not present
                if f"chk_{event_key}" not in st.session_state:
                    st.session_state[f"chk_{event_key}"] = False
                notify = st.checkbox("", key=f"chk_{event_key}")
            with col_info:
                st.subheader(f"**{i+1}. {ev.get('event', '일정명 미정')}**")

                date_str = ev.get('date', '미정')
                time_str = ev.get('time', '미정')
                place_str = ev.get('place', '미정')
                participants_str = ev.get('participants', '미정')

                event_info_html = "<p style='font-size:20px; margin:1px'>"
                if date_str != '미정':
                    event_info_html += f"📅 {date_str} &nbsp;"
                if time_str != '미정':
                    event_info_html += f"⏰ {time_str} &nbsp;"
                if place_str != '미정':
                    event_info_html += f"📍 {place_str} &nbsp;"
                if participants_str != '미정':
                    event_info_html += f"👥 {participants_str}"
                event_info_html += "</p>"
                st.markdown(event_info_html, unsafe_allow_html=True)

            # 줄 2: 알림 시각 설정 (체크했을 때만)
            if notify:
                default_date = datetime.now().date()
                default_hour = datetime.now().hour
                default_minute = datetime.now().minute

                event_date_str = ev.get('date')
                event_time_str = ev.get('time')

                if event_date_str and event_date_str != '미정':
                    try:
                        default_date = datetime.strptime(event_date_str, '%Y-%m-%d').date()
                    except ValueError:
                        pass

                if event_time_str and event_time_str != '미정':
                    try:
                        parsed_time = datetime.strptime(event_time_str, '%H:%M').time()
                        default_hour = parsed_time.hour
                        default_minute = parsed_time.minute
                    except ValueError:
                        pass

                st.markdown("<p style='font-size:20px; font-weight:bold; margin:15px 0'>📅 알림 일정&nbsp;&nbsp;&nbsp;</p>", unsafe_allow_html=True)
                col_d, col_h, col_ht, col_m, col_mt, col_empty = st.columns([0.55, 0.2, 0.1, 0.2, 0.1, 3.8])
                with col_d:
                    a_date = st.date_input("날짜",
                        value=default_date,
                        key=f"d_{i}",
                        label_visibility="collapsed")
                with col_h:
                    a_h = st.number_input("시",
                        min_value=0, max_value=23,
                        value=default_hour,
                        key=f"h_{i}",
                        label_visibility="collapsed")
                with col_ht:
                    st.markdown("<p style='font-size:17px; font-weight:bold; "
                        "padding-top:9px; margin:0'>시</p>",
                        unsafe_allow_html=True)
                with col_m:
                    a_m = st.number_input("분",
                        min_value=0, max_value=59,
                        value=default_minute,
                        key=f"m_{i}",
                        label_visibility="collapsed")
                with col_mt:
                    st.markdown("<p style='font-size:17px; font-weight:bold; "
                        "padding-top:9px; margin:0'>분</p>",
                        unsafe_allow_html=True)
                with col_empty:
                    st.empty()

                # Store selected notification if checkbox is true
                st.session_state.selected_notifications[event_key] = {
                    'event_data': ev,
                    'scheduled_datetime': datetime.combine(a_date, datetime.min.replace(hour=a_h, minute=a_m).time())
                }
        st.divider()

    # 섹션 3: 중요 정보
    st.subheader("⚠️ 중요 정보")
    m = st.session_state.metadata
    t1, t2, t3, t4 = st.tabs(["🔗 링크", "📞 전화번호", "📧 이메일", "🔑 키워드"])
    with t1:
        links = m.get('links', [])
        if links:
            for l in links: st.write(l)
        else: st.caption("발견된 링크가 없습니다.")
    with t2:
        phones = m.get('phones', [])
        if phones:
            for p in phones: st.code(p)
        else: st.caption("발견된 전화번호가 없습니다.")
    with t3:
        emails = m.get('emails', [])
        if emails:
            for e in emails: st.code(e)
        else: st.caption("발견된 이메일이 없습니다.")
    with t4:
        keywords = m.get('keywords', [])
        if keywords:
            st.write(", ".join([f"`{k}`" for k in keywords]))
        else: st.caption("발견된 키워드가 없습니다.")

    # 섹션 4: 요약본 다운로드
    summary_txt = f"================================\n✨ MagiCalendar 요약본\n분석 날짜: {datetime.now().strftime('%Y-%m-%d')}\n================================\n\n"
    summary_txt += f"[📅 발견된 일정 {len(st.session_state.events)}개]\n"
    for i, ev in enumerate(st.session_state.events):
        summary_txt += f"{i+1}. 일정명: {ev.get('event', '미정')}\n   날짜: {ev.get('date', '미정')}\n   시간: {ev.get('time', '미정')}\n   장소: {ev.get('place', '미정')}\n   참여자: {ev.get('participants', '미정')}\n   요약: {ev.get('summary', '미정')}\n\n"

    summary_txt += "[⚠️ 중요 정보]\n🔗 링크:\n"
    if m.get('links'):
        for l in m['links']: summary_txt += f"  - {l}\n"
    else: summary_txt += "  - 발견된 링크가 없습니다.\n"

    summary_txt += "📞 전화번호:\n"
    if m.get('phones'):
        for p in m['phones']: summary_txt += f"  - {p}\n"
    else: summary_txt += "  - 발견된 전화번호가 없습니다.\n"

    summary_txt += "📧 이메일:\n"
    if m.get('emails'):
        for e in m['emails']: summary_txt += f"  - {e}\n"
    else: st.session_state.metadata['emails'] = []

    summary_txt += "🔑 키워드:\n"
    if m.get('keywords'):
        for k in m['keywords']: summary_txt += f"  - {k}\n"
    else: summary_txt += "  - 발견된 키워드가 없습니다.\n"

    summary_txt += f"\n[💬 전체 요약]\n{m.get('global_summary', '요약 정보 없음')}\n================================\n"
    for _ in range(1): st.write("")
    st.divider()
    
    st.subheader("📋 분석 요약본")
    st.code(summary_txt, language=None)
    
    for _ in range(1): st.write("")
    st.divider()
    st.download_button("📄 요약본 TXT 다운로드", data=summary_txt.encode('utf-8-sig'), file_name=f"summary_{datetime.now().strftime('%Y%m%d')}.txt")

    st.subheader("📬 알림 등록")

    # 변수 초기화
    use_email = False
    use_telegram = False
    target_email = ""
    telegram_chat_id = ""

    for _ in range(8): st.write("")
    # 1. 이메일 알림 섹션
    use_email = st.checkbox("📧 이메일 알림", value=False, key="use_email_checkbox")
    for _ in range(15): st.write("")

    if use_email:
        # 입력란 너비를 반으로 줄이기 위해 내부 컬럼 사용
        col_input_half, _ = st.columns([1, 2])
        with col_input_half:
            target_email = st.text_input(
                "알림 받을 이메일 주소",
                placeholder="예: abc@gmail.com, def@naver.com",
                help="여러 명에게 보내려면 쉼표(,)로 구분해서 입력하세요",
                key="target_email_input")
    for _ in range(15): st.write("")
## 2. 텔레그램 알림 섹션
    use_telegram = st.checkbox("💬 텔레그램 알림", value=False, key="use_telegram_checkbox")
    for _ in range(10): st.write("")
    if use_telegram:
        for _ in range(10): st.write("")

    # Chat ID 입력란 (요청하신 변수명 TELEGRAM_CHAT_ID 사용)
        col_chatid_half, _ = st.columns([1, 2])
        for _ in range(11): st.write("")
        with col_chatid_half:
            telegram_chat_id = st.text_input("Chat ID 입력", key="tg_chatid_input")
            for _ in range(11): st.write("")
            if not telegram_chat_id:
                # 상세 방법 (입력 시 이 부분 전체가 사라짐)
                with st.expander("🔍 Chat ID 얻는 방법 확인하기"):
                    st.markdown("""
                    1. 텔레그램에 접속 후 '대화'->'검색'창
                    2. **'@MagiCalendarBot'** 을 검색
                    3. '시작' 버튼을 누르세요.
                    4. '/myid' 를 입력하면 봇이 Chat ID 숫자를 알려줘요!
                    5. 받은 숫자를 위 Chat ID 입력창에 넣으면 돼요.
                    """)
                    st.code("@MagiCalendarBot", language=None)
                    st.markdown(
                        "<div style='text-align: right;'>✴️ 봇 아이디의 오른쪽 버튼을 누르면 복사가 돼요!☝️</div>",
                        unsafe_allow_html=True
                    )
    if st.button("🔔 알림 예약 완료"):
        selected_notifications = st.session_state.get('selected_notifications', {})
        selected_notifications_to_send = {
            k: v for k, v in st.session_state.selected_notifications.items()
            if st.session_state.get(f"chk_{k}", False)
        }

        email_list = []
        if use_email and target_email:
            email_list = [e.strip() for e in target_email.split(",")]
            invalid_emails = [e for e in email_list if "@" not in e or "." not in e]
        else:
            invalid_emails = []

        if not use_email and not use_telegram:
            st.warning("⚠️ 이메일 알림 또는 텔레그램 알림 중 하나를 선택해주세요.")
        elif use_email and not target_email:
            st.error("⚠️ 이메일 주소를 입력해주세요.")
        elif use_email and invalid_emails:
            st.error(f"⚠️ 유효하지 않은 이메일 주소: {', '.join(invalid_emails)}")
        elif use_telegram and (not telegram_chat_id):
            st.error("⚠️ Chat ID를 입력해주세요.")
        elif not selected_notifications_to_send:
            st.warning("⚠️ 알림 받을 일정을 체크박스로 선택해주세요.")
        else:
            success_count = 0
            fail_count = 0
            
            for ed in selected_notifications_to_send.values():
                try:
                    save_alarm_to_sheets(
                        ", ".join(email_list) if use_email else "",
                        telegram_chat_id if use_telegram else "",
                        ed['event_data'],
                        ed['scheduled_datetime']
                    )
                    success_count += 1
                except Exception as e:
                    fail_count += 1

            if success_count > 0 and fail_count == 0:
                st.success(f"✅ {success_count}개 일정 알림이 예약됐어요!")
                st.balloons()
            elif success_count > 0 and fail_count > 0:
                st.warning(f"⚠️ {success_count}개 성공, {fail_count}개 실패했어요. 다시 확인해주세요.")
            else:
                st.error("❌ 알림 예약에 실패했습니다. 다시 시도해주세요.")
