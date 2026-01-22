
import ui
import json
import os
from datetime import datetime

class EthosTest(ui.View):
    def __init__(self):
        self.name = "🕷️ ETHOS++ Test Module"
        self.background_color = 'black'
        self.frame = (0, 0, 360, 600)
        self.questions = self.load_questions()
        self.answers = {}
        self.current_index = 0
        self.init_ui()

    def load_questions(self):
        # Full 30-question list from Nexus ego coding
        q_texts = [
            "How often do you bring up your own wins?",
            "How do you react to criticism?",
            "Do you feel bad if no one notices your effort?",
            "Do you compare yourself to others often?",
            "Can you accept others' opinions when you think you're right?",
            "Do you tune out when the topic isn’t about you?",
            "Who do you blame when you fail?",
            "If you win a prize with someone, how do you split it?",
            "Do others' success lift or bug you?",
            "How much resentment do you still carry?",
            "How hard is it to admit when you mess up?",
            "Do you expect leniency when you're late?",
            "Do you rush to prove doubters wrong?",
            "Do you have to lead team efforts your way?",
            "Do you plot revenge when wronged?",
            "How often do you seek compliments covertly?",
            "Do you downplay others who outshine you?",
            "Do you still hold grudges after apologies?",
            "How much do you care about appearances?",
            "Do you push back when you don't get your way?",
            "Do you fake it when unsure?",
            "Do you enjoy watching rivals mess up?",
            "Do you feel you deserve more than you have?",
            "Do you boast when you win?",
            "Do you hide fear of failure?",
            "Do you own your shame or double down?",
            "Do you need to be the smartest in the room?",
            "Do you call it out if someone takes your credit?",
            "Do you secretly feel above hardship?",
            "How much control do you crave over uncertainty?"
        ]
        return [{"id": i + 1, "text": q_texts[i]} for i in range(len(q_texts))]

    def init_ui(self):
        self.label = ui.Label(frame=(10, 20, 340, 80))
        self.label.font = ('<System-Bold>', 13)
        self.label.text_color = 'white'
        self.label.number_of_lines = 3
        self.label.alignment = ui.ALIGN_LEFT
        self.add_subview(self.label)

        self.slider = ui.Slider(frame=(10, 110, 340, 40))
        self.slider.continuous = True
        self.slider.action = self.slider_action
        self.slider.value = 0.5
        self.add_subview(self.slider)

        self.slider_value_label = ui.Label(frame=(10, 150, 340, 30))
        self.slider_value_label.text_color = '#00FFFF'
        self.slider_value_label.alignment = ui.ALIGN_CENTER
        self.add_subview(self.slider_value_label)

        self.next_btn = ui.Button(title='Next', frame=(130, 200, 100, 40))
        self.next_btn.background_color = '#222222'
        self.next_btn.tint_color = 'white'
        self.next_btn.border_width = 1
        self.next_btn.border_color = '#00FFFF'
        self.next_btn.action = self.next_question
        self.add_subview(self.next_btn)

        self.feedback = ui.TextView(frame=(10, 260, 340, 300))
        self.feedback.text_color = 'white'
        self.feedback.background_color = '#111111'
        self.feedback.font = ('<System>', 12)
        self.feedback.editable = False
        self.add_subview(self.feedback)

        self.update_question()

    def slider_action(self, sender):
        value = int(sender.value * 4) + 1
        self.slider_value_label.text = f"Your score: {value}"

    def update_question(self):
        q = self.questions[self.current_index]
        self.label.text = f"Q{q['id']}: {q['text']}"
        self.slider_value_label.text = f"Your score: {int(self.slider.value * 4) + 1}"

    def next_question(self, sender):
        score = int(self.slider.value * 4) + 1
        qid = self.questions[self.current_index]["id"]
        self.answers[qid] = score
        self.current_index += 1

        if self.current_index < len(self.questions):
            self.update_question()
        else:
            self.finish_test()

    def finish_test(self):
        total = sum(self.answers.values())
        if total <= 50:
            rating = "Very low ego — Grounded, self-aware"
        elif total <= 80:
            rating = "Low-to-moderate ego — Balanced"
        elif total <= 110:
            rating = "Moderate ego — Some challenges"
        else:
            rating = "High ego — Prone to conflict and instability"

        result = {
            "user": "🔥🐜🥸",
            "timestamp": datetime.now().isoformat(),
            "total_score": total,
            "rating": rating,
            "answers": self.answers
        }

        path = os.path.expanduser("~/Documents/ethos_test_result.json")
        with open(path, "w") as f:
            json.dump(result, f, indent=2)

        self.feedback.text = f"✅ Test Complete\nScore: {total}\n{rating}\nSaved to: {path}"

view = EthosTest()
view.present('sheet')
