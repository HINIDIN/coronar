import streamlit as st
import re

# Полные названия → родительный падеж
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

# Сокращения → полное название
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

def find_artery_in_line(line):
    line_lower = line.lower().strip()
    # Убираем возможные двоеточия и лишние символы
    line_clean = re.sub(r'[^\w\s]', ' ', line_lower)
    
    # Проверяем сокращения (в порядке длины, чтобы избежать пересечений)
    for abbr in sorted(ABBREVIATIONS.keys(), key=len, reverse=True):
        if re.search(r'\b' + re.escape(abbr) + r'\b', line_clean):
            return ABBREVIATIONS[abbr]
    
    # Проверяем полные названия
    for full in ARTERIES.keys():
        if full.lower() in line_clean:
            return full
    return None

def parse_coronary_report(text):
    if not text.strip():
        return "Введите заключение коронарографии."
    
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    findings = []

    for line in lines:
        artery_full = find_artery_in_line(line)
        if not artery_full:
            continue

        if artery_full not in ARTERIES:
            continue

        genitive = ARTERIES[artery_full]

        # Анализируем строку
        occlusion = bool(re.search(r'окклюзия', line, re.IGNORECASE))
        stenosis_match = re.search(r'(\d+)%', line)
        percent = int(stenosis_match.group(1)) if stenosis_match else None

        has_stent = bool(re.search(r'стент', line, re.IGNORECASE))
        no_restenosis = bool(re.search(r'без\s+рестеноза', line, re.IGNORECASE))
        has_restenosis = bool(re.search(r'рестеноз', line, re.IGNORECASE)) and not no_restenosis

        findings.append({
            'artery': artery_full,
            'genitive': genitive,
            'occlusion': occlusion,
            'percent': percent,
            'has_stent': has_stent,
            'no_restenosis': no_restenosis,
            'has_restenosis': has_restenosis,
            'raw_line': line
        })

    # Определяем тип диагноза
    has_significant = any(
        f['occlusion'] or (f['percent'] is not None and f['percent'] >= 50)
        for f in findings
    )
    has_atherosclerosis = any(
        f['occlusion'] or 
        f['percent'] is not None or 
        re.search(r'неровн|кальц|атероскл|поражен|бляшк|сужение|бифуркац', f['raw_line'], re.IGNORECASE)
        for f in findings
    )
    has_stents = any(f['has_stent'] for f in findings)

    # === Формирование диагноза ===
    if has_significant:
        parts = []
        for f in findings:
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
        for f in findings:
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
