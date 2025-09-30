import streamlit as st
import re

ARTERIES = {
    "передняя нисходящая артерия": "передней нисходящей артерии",
    "огибающая артерия": "огибающей артерии",
    "правая коронарная артерия": "правой коронарной артерии",
    "ствол левой коронарной артерии": "ствола левой коронарной артерии",
    "диагональная ветвь": "диагональной ветви",
    "ветвь тупого края": "ветви тупого края",
    "задняя межжелудочковая ветвь": "задней межжелудочковой ветви",
    "левая желудочковая ветвь": "левой желудочковой ветви",
    "промежуточная артерия": "промежуточной артерии",
}

ABBREVIATIONS = {
    "пна": "передняя нисходящая артерия",
    "оа": "огибающая артерия",
    "пка": "правая коронарная артерия",
    "лка": "ствол левой коронарной артерии",
    "ствол": "ствол левой коронарной артерии",
    "дб": "диагональная ветвь",
    "дв": "диагональная ветвь",
    "змжв": "задняя межжелудочковая ветвь",
    "лжв": "левая желудочковая ветвь",
    "втк": "ветвь тупого края",
    "па": "промежуточная артерия",
}

def find_percent_near(text, keyword):
    text_lower = text.lower()
    keyword_lower = keyword.lower()
    pos = text_lower.find(keyword_lower)
    if pos == -1:
        return None
    start = max(0, pos - 30)
    end = min(len(text), pos + 50)
    window = text[start:end]
    percents = re.findall(r'(\d+)%', window)
    return int(percents[0]) if percents else None

def parse_coronary_report(text):
    if not text.strip():
        return "Введите заключение коронарографии."
    
    # Объединяем весь текст в одну строку для поиска
    full_text = " " + text + " "
    findings = {}
    
    # 1. Ищем все упоминания: "АББР ХХ%" или "АББР (ХХ%)"
    for abbr, full_name in ABBREVIATIONS.items():
        if full_name not in ARTERIES:
            continue
        # Шаблон: " аббревиатура 80%" или " аббревиатура (80%)"
        pattern = r'\b' + re.escape(abbr) + r'\s*[\(\-]?\s*(\d+)%'
        matches = re.findall(pattern, full_text, re.IGNORECASE)
        if matches:
            percent = int(matches[0])  # берём первое вхождение (обычно одно)
            findings[full_name] = {
                'percent': percent,
                'occlusion': False,
                'genitive': ARTERIES[full_name]
            }
    
    # 2. Ищем окклюзии по сокращениям и полным названиям
    for abbr, full_name in ABBREVIATIONS.items():
        if full_name not in ARTERIES:
            continue
        # Ищем: "окклюзия ... аббревиатура" или "аббревиатура ... окклюзия"
        pattern = r'\bокклюзия\b.*?\b' + re.escape(abbr) + r'\b|\b' + re.escape(abbr) + r'.*?\bокклюзия\b'
        if re.search(pattern, full_text, re.IGNORECASE):
            if full_name not in findings:
                findings[full_name] = {'percent': None, 'occlusion': True, 'genitive': ARTERIES[full_name]}
            else:
                findings[full_name]['occlusion'] = True
    
    # 3. Также проверим полные названия на окклюзию (на всякий случай)
    for full_name in ARTERIES.keys():
        pattern = r'\bокклюзия\b.*?\b' + re.escape(full_name) + r'\b|\b' + re.escape(full_name) + r'.*?\bокклюзия\b'
        if re.search(pattern, full_text, re.IGNORECASE):
            if full_name not in findings:
                findings[full_name] = {'percent': None, 'occlusion': True, 'genitive': ARTERIES[full_name]}
            else:
                findings[full_name]['occlusion'] = True

    # Преобразуем в список
    findings_list = []
    for full_name, data in findings.items():
        findings_list.append({
            'artery': full_name,
            'genitive': data['genitive'],
            'occlusion': data['occlusion'],
            'percent': data['percent'],
            'has_stent': bool(re.search(r'стент', full_text, re.IGNORECASE)),
            'no_restenosis': bool(re.search(r'без\s+рестеноза', full_text, re.IGNORECASE)),
            'has_restenosis': bool(re.search(r'рестеноз', full_text, re.IGNORECASE)) and not bool(re.search(r'без\s+рестеноза', full_text, re.IGNORECASE)),
            'raw_line': ''
        })

    # Остальная логика — без изменений
    has_significant = any(
        f['occlusion'] or (f['percent'] is not None and f['percent'] >= 50)
        for f in findings_list
    )
    has_atherosclerosis = any(
        f['occlusion'] or 
        f['percent'] is not None or 
        re.search(r'неровн|кальц|атероскл|поражен|бляшк|сужение|бифуркац', text, re.IGNORECASE)
        for f in findings_list
    )
    has_stents = any(f['has_stent'] for f in findings_list)

    if has_significant:
        parts = []
        for f in findings_list:
            desc = ""
            if f['occlusion']:
                desc = f"Окклюзия {f['genitive']}"
            elif f['percent'] is not None and f['percent'] >= 50:
                desc = f"Стеноз {f['genitive']} {f['percent']}%"
            else:
                if f['has_stent']:
                    stent_str = "стент"
                    if f['no_restenosis']:
                        stent_str += " без рестеноза"
                    elif f['has_restenosis']:
                        stent_str += " с рестенозом"
                    else:
                        stent_str += " (состояние не уточнено)"
                    desc = f"Стент {f['genitive']} {stent_str.split(' ', 1)[1]}"
                else:
                    continue

            if f['has_stent'] and (f['occlusion'] or (f['percent'] is not None and f['percent'] >= 50)):
                stent_str = "стент"
                if f['no_restenosis']:
                    stent_str += " без рестеноза"
                elif f['has_restenosis']:
                    stent_str += " с рестенозом"
                else:
                    stent_str += " (состояние не уточнено)"
                desc += f", {stent_str}"

            if desc:
                parts.append(desc)

        diagnosis = "Атеросклероз коронарных артерий."
        if parts:
            diagnosis += " " + ". ".join(parts) + "."
        return diagnosis

    elif has_atherosclerosis or has_stents:
        stent_parts = []
        for f in findings_list:
            if f['has_stent']:
                stent_str = f"Стент {f['genitive']}"
                if f['no_restenosis']:
                    stent_str += " без рестеноза"
                elif f['has_restenosis']:
                    stent_str += " с рестенозом"
                else:
                    stent_str += " (состояние не уточнено)"
                stent_parts.append(stent_str)
        diagnosis = "Нестенозирующий атеросклероз коронарных артерий."
        if stent_parts:
            diagnosis += " " + ". ".join(stent_parts) + "."
        return diagnosis

    else:
        return "Интактные коронарные артерии."

# === Streamlit UI ===
st.set_page_config(page_title="Коронарография → Диагноз", page_icon="🫀")
st.title("🫀 Преобразование заключения коронарографии в диагноз")

user_input = st.text_area("Вставьте заключение:", height=300, value="""Ствол ЛКА:  без поражений. 
ПНА:  с поражениями, бифуркационный стеноз ПНА (80%)-ДВ (90%) (1:1:1 по Medina)
ОА:  с поражениями, окклюзия в д/3, заполняется внутрисистемно
ПКА:  с поражениями, стеноз в с/3 40%, в д/3 75%, стеноз в устье ЗМЖВ 75%, стеноз ЛЖВ 99%""")

if st.button("Сформировать диагноз", type="primary"):
    diagnosis = parse_coronary_report(user_input)
    st.subheader("Диагноз:")
    st.write(diagnosis)
