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
