# genetics_engine.py - РАСШИРЕННАЯ ВЕРСИЯ
"""
Модуль для интерпретации генетических данных
Поддерживает основные гены: MTHFR, FTO, ACTN3, и другие
"""

class GeneticsEngine:
    # Словарь для нормализации ввода
    GENOTYPE_MAPPING = {
        # MTHFR
        "c/c": "C/C", "cc": "C/C", "норма": "C/C",
        "c/t": "C/T", "ct": "C/T", "гетерозигота": "C/T",
        "t/t": "T/T", "tt": "T/T", "гомозигота": "T/T",
        
        # FTO
        "t/t": "T/T", "tt": "T/T", "нормальный": "T/T",
        "a/t": "A/T", "at": "A/T", "повышенный": "A/T",
        "a/a": "A/A", "aa": "A/A", "высокий": "A/A",
        
        # ACTN3
        "r/r": "R/R", "rr": "R/R", "r/r": "R/R", "взрывной": "R/R",
        "r/x": "R/X", "rx": "R/X", "r/x": "R/X",
        "x/x": "X/X", "xx": "X/X", "выносливый": "X/X",
    }
    
    @classmethod
    def normalize_genotype(cls, genotype: str) -> str:
        """Нормализует ввод генотипа"""
        if not genotype:
            return ""
        
        genotype = genotype.lower().strip()
        # Убираем лишние символы
        genotype = genotype.replace('/', '').replace(' ', '').replace('-', '')
        
        # Прямое соответствие
        if genotype in cls.GENOTYPE_MAPPING:
            return cls.GENOTYPE_MAPPING[genotype]
        
        # Частичное соответствие
        for key, value in cls.GENOTYPE_MAPPING.items():
            if key in genotype:
                return value
        
        return genotype.upper()
    
    @staticmethod
    def interpret_mthfr(genotype):
        """Интерпретация гена MTHFR (фолатный цикл)"""
        if not genotype:
            return None
        
        # Нормализуем генотип
        genotype = GeneticsEngine.normalize_genotype(genotype)
        
        if genotype in ["C/C", "CC"]:
            return {
                "gene": "MTHFR",
                "status": "✅ Норма",
                "risk": "Низкий",
                "description": "Фолатный цикл работает нормально. Обычная фолиевая кислота усваивается хорошо.",
                "advice": "Достаточно 400 мкг/день фолиевой кислоты из пищи или стандартных добавок.",
                "supplements": "Фолиевая кислота 400 мкг/день",
                "foods": "Зеленые листовые овощи, бобовые, цитрусовые, печень",
                "checkups": "Стандартный контроль здоровья"
            }
        elif genotype in ["C/T", "CT"]:
            return {
                "gene": "MTHFR",
                "status": "⚠️ Гетерозигота",
                "risk": "Средний",
                "description": "Активность фермента MTHFR снижена на 30-40%. Это влияет на превращение фолиевой кислоты в активную форму.",
                "advice": "Рекомендуется метилфолат (L-метилфолат) вместо обычной фолиевой кислоты.",
                "supplements": "Метилфолат 400-800 мкг/день",
                "foods": "Печень, шпинат, спаржа, брокколи (но в комплексе с метилфолатом)",
                "checkups": "Контроль гомоцистеина раз в год"
            }
        elif genotype in ["T/T", "TT"]:
            return {
                "gene": "MTHFR",
                "status": "🔴 Гомозигота",
                "risk": "Высокий",
                "description": "Активность MTHFR снижена на 70%. Значительно повышен риск гипергомоцистеинемии.",
                "advice": "ОБЯЗАТЕЛЕН метилфолат в высоких дозах. Добавь витамин B12 для синергии.",
                "supplements": "Метилфолат 800-1000 мкг/день + метилкобаламин (B12) 1000 мкг/день",
                "foods": "Регулярное употребление продуктов, богатых фолатами: печень, шпинат, спаржа",
                "checkups": "Регулярный контроль гомоцистеина (каждые 3-6 месяцев)"
            }
        return None
    
    @staticmethod
    def interpret_fto(genotype):
        """Интерпретация гена FTO (риск ожирения)"""
        if not genotype:
            return None
        
        genotype = GeneticsEngine.normalize_genotype(genotype)
        
        if genotype in ["T/T", "TT"]:
            return {
                "gene": "FTO",
                "status": "✅ Нормальный риск",
                "risk": "Низкий",
                "description": "Базовый риск ожирения. Ген не влияет на аппетит и насыщение.",
                "advice": "Стандартные рекомендации по питанию. Физическая активность важна для общего здоровья.",
                "nutrition": "30% белка, 30% жиров, 40% углеводов",
                "warning": "Исследования показывают, что у носителей TT нет повышенного риска ожирения",
                "tips": [
                    "Сбалансированное питание",
                    "Регулярная физическая активность",
                    "Контроль порций по желанию"
                ]
            }
        elif genotype in ["A/T", "AT"]:
            return {
                "gene": "FTO",
                "status": "⚠️ Повышенный риск",
                "risk": "Средний",
                "description": "Повышенный риск ожирения (+20% к ИМТ). Снижено чувство насыщения, повышен аппетит.",
                "advice": "Ключевое значение имеет физическая активность и контроль питания.",
                "nutrition": "Белковый завтрак (30г белка), начинать еду с овощей, контроль порций",
                "warning": "Физическая активность СНИЖАЕТ риск на 30%! Минимум 10 000 шагов/день",
                "tips": [
                    "Обязательный завтрак с высоким содержанием белка",
                    "Клетчатка перед каждым основным приемом пищи",
                    "Исключить сахар и простые углеводы",
                    "Ежедневная физическая активность"
                ]
            }
        elif genotype in ["A/A", "AA"]:
            return {
                "gene": "FTO",
                "status": "🔴 Высокий риск",
                "risk": "Высокий",
                "description": "Высокий риск ожирения (на 280 ккал/день больше). Значительно повышенная тяга к еде, позднее насыщение.",
                "advice": "⚠️ КРИТИЧЕСКИ ВАЖНО: физическая активность и строгий контроль питания.",
                "nutrition": "Белок 30г на завтрак, клетчатка перед каждым приемом пищи, исключить сахар и трансжиры",
                "warning": "НЕ менее 150 мин физической активности в неделю! Активность нивелирует эффект гена",
                "tips": [
                    "Строгий контроль калорий",
                    "Еженедельное взвешивание",
                    "Исключить все переработанные продукты",
                    "Минимум 10 000 шагов ежедневно",
                    "Силовые тренировки 2-3 раза в неделю"
                ]
            }
        return None
    
    @staticmethod
    def interpret_actn3(genotype):
        """Интерпретация гена ACTN3 (тип мышечных волокон)"""
        if not genotype:
            return None
        
        genotype = GeneticsEngine.normalize_genotype(genotype)
        
        if genotype in ["R/R", "RR", "R/RR"]:
            return {
                "gene": "ACTN3",
                "status": "💪 Взрывной тип (RR)",
                "description": "Преобладание быстрых мышечных волокон (тип II). Отличная предрасположенность к спринту и силовым видам спорта.",
                "advice": "Силовые тренировки 3-4 раза в неделю, HIIT, спринт, взрывные нагрузки.",
                "training": [
                    "Силовые тренировки (3-4 раза/неделю)",
                    "HIIT, спринтерские интервалы",
                    "Взрывные упражнения (плиометрика)",
                    "Кроссфит"
                ],
                "warning": "Восстановление может требовать больше времени после интенсивных нагрузок. Уделяй внимание растяжке."
            }
        elif genotype in ["R/X", "RX", "R/X"]:
            return {
                "gene": "ACTN3",
                "status": "💪 Смешанный тип (RX)",
                "description": "Сбалансированное соотношение быстрых и медленных мышечных волокон. Универсальный тип.",
                "advice": "Хорошо подходят как силовые, так и аэробные нагрузки. Можно чередовать.",
                "training": [
                    "Чередование силовых и кардио (2+2 в неделю)",
                    "Смешанные тренировки",
                    "Функциональный тренинг"
                ],
                "warning": "Хорошая адаптация к разным типам нагрузок. Следи за восстановлением."
            }
        elif genotype in ["X/X", "XX"]:
            return {
                "gene": "ACTN3",
                "status": "🏃 Выносливый тип (XX)",
                "description": "Преобладание медленных мышечных волокон (тип I). Предрасположенность к длительным аэробным нагрузкам.",
                "advice": "Бег, плавание, велосипед, длительные аэробные нагрузки. HIIT тоже возможен, но упор на endurance.",
                "training": [
                    "Длительные кардио-тренировки (40-60 мин)",
                    "Бег, плавание, велосипед",
                    "Аэробные классы",
                    "Умеренные силовые с большим количеством повторений"
                ],
                "warning": "HIIT и взрывные нагрузки даются хуже, но тренируемы. Уделяй внимание вариативности."
            }
        return None
    
    @staticmethod
    def interpret_genes(genes_dict):
        """
        Интерпретирует несколько генов сразу
        
        Args:
            genes_dict: Словарь вида {"mthfr": "C/T", "fto": "AT", "actn3": "RR"}
        
        Returns:
            Словарь с интерпретациями
        """
        result = {}
        
        if "mthfr" in genes_dict:
            result["mthfr"] = GeneticsEngine.interpret_mthfr(genes_dict["mthfr"])
        
        if "fto" in genes_dict:
            result["fto"] = GeneticsEngine.interpret_fto(genes_dict["fto"])
        
        if "actn3" in genes_dict:
            result["actn3"] = GeneticsEngine.interpret_actn3(genes_dict["actn3"])
        
        return result
    
    @staticmethod
    def generate_full_report(mthfr_input, fto_input, actn3_input):
        """Генерирует полный отчет по трем генам"""
        
        # Интерпретируем каждый ген
        mthfr = GeneticsEngine.interpret_mthfr(mthfr_input)
        fto = GeneticsEngine.interpret_fto(fto_input)
        actn3 = GeneticsEngine.interpret_actn3(actn3_input)
        
        # Формируем текстовые части
        mthfr_text = f"{mthfr['status']}: {mthfr['description']}" if mthfr else "❓ MTHFR: не определено"
        fto_text = f"{fto['status']}: {fto['description']}" if fto else "❓ FTO: не определено"
        actn3_text = f"{actn3['status']}: {actn3['description']}" if actn3 else "❓ ACTN3: не определено"
        
        # Собираем рекомендации
        nutrition_advice = []
        training_advice = []
        supplement_advice = []
        
        # MTHFR рекомендации (БАДы)
        if mthfr:
            supplement_advice.append(f"• MTHFR: {mthfr['supplements']}")
            supplement_advice.append(f"• Продукты: {mthfr['foods']}")
        
        # FTO рекомендации (питание)
        if fto:
            if fto['status'].startswith('⚠️') or fto['status'].startswith('🔴'):
                nutrition_advice.append(f"• FTO: {fto['advice']}")
                for tip in fto.get('tips', []):
                    nutrition_advice.append(f"  • {tip}")
            else:
                nutrition_advice.append(f"• FTO: {fto['advice']}")
        
        # ACTN3 рекомендации (тренировки)
        if actn3:
            training_advice.append(f"• ACTN3: {actn3['advice']}")
            for training in actn3.get('training', [])[:3]:
                training_advice.append(f"  • {training}")
        
        # Добавляем общие рекомендации, если чего-то не хватает
        if not supplement_advice:
            supplement_advice.append("• Базовые добавки: Омега-3 (2г/день), Витамин D (2000-5000 МЕ), Магний (400 мг)")
        
        if not nutrition_advice:
            nutrition_advice.append("• Стандартные рекомендации: 30% белка, 30% жиров, 40% углеводов")
            nutrition_advice.append("• Питьевой режим: 30-35 мл на кг веса")
        
        if not training_advice:
            training_advice.append("• Смешанный тип тренировок: 2 силовых + 2 кардио в неделю")
            training_advice.append("• 10 000 шагов ежедневно")
        
        return {
            "mthfr_text": mthfr_text,
            "fto_text": fto_text,
            "actn3_text": actn3_text,
            "nutrition_advice": "\n".join(nutrition_advice),
            "training_advice": "\n".join(training_advice),
            "supplement_advice": "\n".join(supplement_advice),
            "full_report": f"""🧬 **ТВОЙ ГЕНЕТИЧЕСКИЙ ПРОФИЛЬ**

**MTHFR** (фолатный цикл)
{mthfr_text}

**FTO** (риск ожирения)
{fto_text}

**ACTN3** (тип мышц)
{actn3_text}

📋 **РЕКОМЕНДАЦИИ:**

🥗 **ПИТАНИЕ:**
{chr(10).join(['  ' + line for line in nutrition_advice])}

💪 **ТРЕНИРОВКИ:**
{chr(10).join(['  ' + line for line in training_advice])}

💊 **БАДЫ:**
{chr(10).join(['  ' + line for line in supplement_advice])}

⚠️ *Рекомендации основаны на научных данных и требуют консультации с врачом.*
"""
        } 