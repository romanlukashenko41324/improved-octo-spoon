import json
import random
import time
from dataclasses import dataclass, field

# -----------------------------
# Константи балансу (можна змінювати)
# -----------------------------
MAX_NEED = 100
TICK = 1  # секунда між кроками анімації/логіки (для затишку; можна = 0)

@dataclass
class Needs:
    hunger: int = 60
    energy: int = 60
    hygiene: int = 60
    mood: int = 60

    def clamp(self):
        self.hunger = max(0, min(MAX_NEED, self.hunger))
        self.energy = max(0, min(MAX_NEED, self.energy))
        self.hygiene = max(0, min(MAX_NEED, self.hygiene))
        self.mood = max(0, min(MAX_NEED, self.mood))

@dataclass
class Skills:
    cooking: int = 0
    fitness: int = 0
    logic: int = 0

    def gain(self, skill_name: str, amount: int = 1):
        current = getattr(self, skill_name)
        setattr(self, skill_name, min(10, current + amount))  # максимум 10

@dataclass
class Inventory:
    money: int = 100
    food: int = 3

@dataclass
class Job:
    title: str = "Інтерн"
    base_salary: int = 50  # за день
    required_logic: int = 2

    def compute_salary(self, sim) -> int:
        logic_bonus = max(0, sim.skills.logic - self.required_logic) * 10
        mood_multiplier = 1.0 if sim.needs.mood >= 50 else 0.7
        return int((self.base_salary + logic_bonus) * mood_multiplier)

@dataclass
class Sim:
    name: str
    day: int = 1
    hour: int = 7  # стартуємо з ранку
    needs: Needs = field(default_factory=Needs)
    skills: Skills = field(default_factory=Skills)
    inventory: Inventory = field(default_factory=Inventory)
    job: Job = field(default_factory=Job)
    sick: bool = False

    # -----------------------------
    # Базова логіка часу/потреб
    # -----------------------------
    def tick(self, hours: int = 1):
        # Пасивне падіння потреб
        self.needs.hunger -= 5 * hours
        self.needs.energy -= 5 * hours
        self.needs.hygiene -= 2 * hours
        self.needs.mood -= 1 * hours

        # Штрафи за критичні стани
        if self.needs.hunger < 20:
            self.needs.mood -= 3 * hours
        if self.needs.energy < 20:
            self.needs.mood -= 3 * hours
        if self.needs.hygiene < 20:
            self.needs.mood -= 2 * hours

        # Хвороба дає додаткові штрафи
        if self.sick:
            self.needs.energy -= 4 * hours
            self.needs.mood -= 2 * hours

        self.needs.clamp()
        self.advance_time(hours)

    def advance_time(self, hours: int):
        self.hour += hours
        if self.hour >= 24:
            self.hour -= 24
            self.day += 1
            self.daily_event()

    def daily_event(self):
        # Випадок дня: 50% шансу на щось
        if random.random() < 0.5:
            event_type = random.choice(["гарна_новина", "неприємність", "здоров'я"])
            if event_type == "гарна_новина":
                delta = random.randint(5, 15)
                self.needs.mood += delta
                print(f"• {self.name} отримав(ла) гарну новину! Настрій +{delta}.")
            elif event_type == "неприємність":
                delta = random.randint(5, 10)
                self.needs.mood -= delta
                print(f"• Сталася неприємність… Настрій -{delta}.")
            else:
                # ризик захворіти
                if random.random() < 0.25:
                    self.sick = True
                    print("• Ви захворіли. Енергія падає швидше, настрій гіршає.")
        self.needs.clamp()

    # -----------------------------
    # Дії гравця
    # -----------------------------
    def eat(self):
        if self.inventory.food <= 0:
            # автопокупка
            cost = 10
            if self.inventory.money >= cost:
                self.inventory.money -= cost
                self.inventory.food += 1
                print("• Автопокупка продуктів: -10₴, +1 їжа.")
            else:
                print("• Немає їжі і грошей. Спробуйте попрацювати або відпочити.")
                return

        self.inventory.food -= 1
        restore = 30 + self.skills.cooking * 3
        self.needs.hunger += restore
        self.needs.mood += 5
        self.tick(hours=1)
        print(f"• Прийом їжі: голод +{restore}, настрій +5.")

    def sleep(self, hours: int = 6):
        restore_energy = min(MAX_NEED - self.needs.energy, 12 * hours)
        self.needs.energy += restore_energy
        self.needs.hygiene -= 2 * hours  # трохи падає гігієна
        self.needs.mood += 3
        # під час сну час іде
        self.tick(hours=hours)
        print(f"• Сон {hours} год: енергія +{restore_energy}, настрій +3, гігієна -{2*hours}.")

    def shower(self):
        restore = 35
        self.needs.hygiene += restore
        self.needs.mood += 4
        self.tick(hours=1)
        print(f"• Душ: гігієна +{restore}, настрій +4.")

    def work(self, hours: int = 8):
        if self.sick:
            print("• Ви почуваєтесь зле. Робота менш ефективна.")
        salary = self.job.compute_salary(self)
        # Враховуємо відпрацьовані години (пропорційно)
        earned = int(salary * (hours / 8.0) * (0.7 if self.sick else 1.0))
        self.inventory.money += earned

        # Втома, голод, гігієна падають
        self.needs.energy -= 6 * hours
        self.needs.hunger -= 4 * hours
        self.needs.hygiene -= 3 * hours
        self.needs.mood += 2  # продуктивність трохи радує

        self.tick(hours=hours)
        print(f"• Робота {hours} год: +{earned}₴, енергія -{6*hours}, голод -{4*hours}, гігієна -{3*hours}.")

    def train_skill(self, skill_name: str, hours: int = 2):
        if skill_name not in ["cooking", "fitness", "logic"]:
            print("• Невідомий навик. Доступні: cooking, fitness, logic.")
            return
        # Тренування: витрати енергії/гігієни, приріст навику
        if skill_name == "fitness":
            self.needs.energy -= 6 * hours
            self.needs.hygiene -= 4 * hours
            gain = 2
        else:
            self.needs.energy -= 4 * hours
            self.needs.hygiene -= 2 * hours
            gain = 2

        self.skills.gain(skill_name, gain)
        self.needs.mood += 5
        self.tick(hours=hours)
        print(f"• Тренування {skill_name}: навик +{gain}, енергія -{4*hours}, гігієна -{2*hours}, настрій +5.")

    def socialize(self, hours: int = 2):
        self.needs.mood += 12
        self.needs.energy -= 2 * hours
        self.needs.hygiene -= 1 * hours
        self.tick(hours=hours)
        print(f"• Спілкування {hours} год: настрій +12, енергія -{2*hours}, гігієна -{hours}.")

    def relax(self, hours: int = 1):
        self.needs.mood += 8
        self.needs.energy += 3
        self.tick(hours=hours)
        print(f"• Відпочинок: настрій +8, енергія +3.")

    def heal(self):
        if not self.sick:
            print("• Ви здорові.")
            return
        # Лікування займає час і гроші
        cost = 30
        if self.inventory.money >= cost:
            self.inventory.money -= cost
            self.sick = False
            self.needs.mood += 10
            self.tick(hours=2)
            print("• Візит до лікаря: -30₴, здоров'я покращилось, настрій +10.")
        else:
            print("• Недостатньо грошей для лікування (потрібно 30₴).")

    # -----------------------------
    # Збереження / Завантаження
    # -----------------------------
    def save(self, path: str = "sim_save.json"):
        data = {
            "name": self.name,
            "day": self.day,
            "hour": self.hour,
            "needs": self.needs.__dict__,
            "skills": self.skills.__dict__,
            "inventory": self.inventory.__dict__,
            "job": self.job.__dict__,
            "sick": self.sick
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"• Збережено у {path}")

    @staticmethod
    def load(path: str = "sim_save.json"):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        sim = Sim(
            name=data["name"],
            day=data["day"],
            hour=data["hour"],
            needs=Needs(**data["needs"]),
            skills=Skills(**data["skills"]),
            inventory=Inventory(**data["inventory"]),
            job=Job(**data["job"]),
        )
        sim.sick = data["sick"]
        print(f"• Завантажено з {path}")
        return sim

# -----------------------------
# Інтерфейс: консольне меню
# -----------------------------
def print_status(sim: Sim):
    print("\n=== Статус ===")
    print(f"День {sim.day}, {sim.hour:02d}:00 | Гроші: {sim.inventory.money}₴, Їжа: {sim.inventory.food}")
    print(f"Голод: {sim.needs.hunger}/100 | Енергія: {sim.needs.energy}/100 | Гігієна: {sim.needs.hygiene}/100 | Настрій: {sim.needs.mood}/100")
    print(f"Навики → Кулінарія: {sim.skills.cooking}, Фітнес: {sim.skills.fitness}, Логіка: {sim.skills.logic}")
    sick_str = "Так" if sim.sick else "Ні"
    print(f"Хворий(а): {sick_str} | Робота: {sim.job.title} (база {sim.job.base_salary}₴/день)")

def main():
    print("Ласкаво просимо у текстовий The Sims!")
    name = input("Введіть ім'я Сіма: ").strip() or "Таня"
    sim = Sim(name=name)

    while True:
        print_status(sim)
        print("\nДії:")
        print("1. Їсти")
        print("2. Спати")
        print("3. Душ")
        print("4. Працювати")
        print("5. Тренувати навик")
        print("6. Спілкуватись")
        print("7. Відпочивати")
        print("8. Лікуватись")
        print("9. Зберегти")
        print("0. Вийти")
        choice = input("Ваш вибір: ").strip()

        if choice == "1":
            sim.eat()
        elif choice == "2":
            hours = int(input("Скільки годин спати? (1-10): ").strip() or "6")
            sim.sleep(max(1, min(10, hours)))
        elif choice == "3":
            sim.shower()
        elif choice == "4":
            hours = int(input("Скільки годин працювати? (1-12): ").strip() or "8")
            sim.work(max(1, min(12, hours)))
        elif choice == "5":
            skill = input("Який навик? (cooking/fitness/logic): ").strip()
            hours = int(input("Скільки годин тренуватись? (1-6): ").strip() or "2")
            sim.train_skill(skill, max(1, min(6, hours)))
        elif choice == "6":
            hours = int(input("Скільки годин спілкуватись? (1-4): ").strip() or "2")
            sim.socialize(max(1, min(4, hours)))
        elif choice == "7":
            hours = int(input("Скільки годин відпочивати? (1-4): ").strip() or "1")
            sim.relax(max(1, min(4, hours)))
        elif choice == "8":
            sim.heal()
        elif choice == "9":
            sim.save()
        elif choice == "0":
            print("До зустрічі!")
            break
        else:
            print("• Невірний вибір.")

        if TICK > 0:
            time.sleep(TICK)

if __name__ == "__main__":
    main()
