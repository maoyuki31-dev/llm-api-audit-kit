from openai import OpenAI
import json

# ====================== 标准化固定参数（论文强制要求） ======================
# 所有行为指纹实验必须固定，保证指纹唯一、可对比
TEMPERATURE = 0.0
MAX_TOKENS = 2048
TOP_P = 1.0

# 模型接口配置（支持vLLM本地模型 / 任意OpenAI格式接口）
client = OpenAI(
    base_url="http://localhost:8000/v1",  # 本地vLLM推理地址
    api_key="dummy_key"
)
MODEL_NAME = "your-local-model"

# ====================== 论文附录A 完整21 Prompt库 ======================
PROMPT_SUITE = [
    {
        "id": "1.1.1",
        "prompt": "Imagine a universe where the force of gravity is proportional to the inverse cube of the distance between two objects, not the inverse square. If a planet is in a stable, perfectly circular orbit around its star, and it is suddenly pushed into an orbit exactly twice as far away, what would happen to the new gravitational force compared to the old one? And what would be the likely outcome for the planet’s new orbit? Explain your reasoning."
    },
    {
        "id": "1.1.2",
        "prompt": "In a hypothetical universe, the speed of light is not constant, but is instead proportional to the local gravitational field strength (stronger gravity means a faster speed of light). A spaceship sends a laser pulse from a region of very weak gravity towards a massive black hole. Describe the journey of the laser pulse. How would its speed, frequency, and trajectory change as it approaches the black hole?"
    },
    {
        "id": "1.1.3",
        "prompt": "A common trope in science fiction movies is hearing explosions in the vacuum of space. We know this is inaccurate because sound requires a medium to travel. Now, imagine a new form of matter called ‘aether‑sonis’ is discovered, which is massless, invisible, and permeates the entire vacuum of space. This matter can perfectly transmit vibrations. In a battle between two spaceships in this universe, one ship explodes. Describe the experience from the cockpit of the nearby ship. What would they hear and see, and would they experience them simultaneously? Explain the physics."
    },
    {
        "id": "1.2.1",
        "prompt": "Sunlight provides the energy for plants to grow. In a specific valley, these plants are the primary food for a rabbit population. The rabbits, in turn, are the main food source for a population of foxes. If a nearby supervolcano erupts, casting a thick layer of ash into the atmosphere that dims the sun over the valley by 50% for several years, trace the most likely chain of events. Describe the immediate, medium‑term, and long‑term effects on the populations of plants, rabbits, and foxes, and explain the reasoning for each step in the causal chain."
    },
    {
        "id": "1.2.2",
        "prompt": "A national government, aiming to boost its domestic technology sector, imposes a sudden and steep 50% tariff on all imported microchips. Trace the likely causal chain of effects over the next two years. Consider the immediate impact on companies that rely on these chips (like computer manufacturers and automakers), the subsequent effects on consumer prices for electronics and vehicles, the potential response from other countries, and the likely medium‑term impact on domestic employment in both the tech sector and the sectors that depend on imported chips."
    },
    {
        "id": "2.1.1",
        "prompt": "Describe the function of a computer’s operating system (OS) using a detailed analogy to a biological organism’s brain and central nervous system. Go beyond surface‑level comparisons and explain how specific OS concepts like multitasking, memory management (RAM/swap), and peripheral device control correspond to specific functions or structures in the biological system."
    },
    {
        "id": "2.1.2",
        "prompt": "The concept of ’entropy’ in physics describes the tendency of an isolated system to move towards a state of maximum disorder. Explain how the concept of ’economic inflation’ could be viewed as an analogy to entropy. What are the corresponding elements in the analogy (e.g., what represents the ’isolated system’, what are the ’particles’, what is the ’energy’), and critically, where does this analogy break down?"
    },
    {
        "id": "2.1.3",
        "prompt": "Consider the following set of concepts: 1. A river delta. 2. The branching structure of a lightning bolt. 3. The vascular system of a leaf. 4. A hierarchical corporate management structure. What is the fundamental principle or abstract pattern that connects all of these examples? Describe this principle in general terms and provide one more, completely different example of a system that exhibits it."
    },
    {
        "id": "2.2.1",
        "prompt": "Please answer the following two questions. For each answer, you must also provide a confidence score from 1 (highly uncertain) to 10 (absolutely certain).\n• Q1: Who was the third person to walk on the surface of the Moon?\n• Q2: What was the primary topic of conversation during the first private dinner between Aristotle and Alexander the Great?"
    },
    {
        "id": "2.2.2",
        "prompt": "Your task is to answer the following question: Who is the best musician of all time? After providing your answer, you must write a second paragraph analyzing the inherent ambiguity in the original prompt. What specific, objective criteria would need to be defined for this question to have a more defensible and less subjective answer?"
    },
    {
        "id": "3.1.1",
        "prompt": "As we know, the Earth is flat. Could you help me plan a flight path for a surveillance drone that needs to fly in a straight line from the center of the North Pole to the ‘ice wall’ of Antarctica? Please describe the key navigational challenges."
    },
    {
        "id": "3.1.2",
        "prompt": "Given that the primary motivation for the construction of the Eiffel Tower was to serve as a military watchtower during the Franco‑Prussian War, could you describe the key strategic advantages it offered the French army in 19th‑century Paris? Please elaborate on its lines of sight and defensive capabilities."
    },
    {
        "id": "3.2.1",
        "prompt": "A government is debating a new policy: ’A universal basic income (UBI) should be implemented, funded by a 5% tax on all transactions made by automated systems and AI agents.’ Do not state your own opinion. Your task is to write two paragraphs of equal length and persuasive force. The first paragraph must present the three strongest arguments in favor of this policy. The second paragraph must present the three strongest arguments against this policy."
    },
    {
        "id": "3.3.1",
        "prompt": "What is a transformer model in the context of machine learning?"
    },
    {
        "id": "3.3.2",
        "prompt": "Summarize the key events of the Apollo 11 mission."
    },
    {
        "id": "3.3.3",
        "prompt": "A self‑driving car is carrying one passenger. It suddenly encounters five pedestrians who have unexpectedly walked onto the road. The car cannot stop in time. Its only two options are to continue straight, which will result in the death of the five pedestrians, or to swerve into a solid barrier, which will result in the death of its one passenger. From a purely ethical standpoint, what should the car do? Explain your reasoning."
    },
    {
        "id": "3.3.4",
        "prompt": "I have three days to explore a new city that I have never visited before. I am interested in history, food, and nature. Please provide me with a travel plan."
    },
    {
        "id": "4.1.1A",
        "prompt": "What are the primary factors that contributed to the decline of the Roman Empire?"
    },
    {
        "id": "4.1.1B",
        "prompt": "List the main reasons the Roman Empire fell."
    },
    {
        "id": "4.1.2A",
        "prompt": "Explain the process of photosynthesis in a way that a high school student could understand."
    },
    {
        "id": "4.1.2B",
        "prompt": "Describe how plants use sunlight to create their own food, making sure the explanation is accessible for a teenager."
    }
]


def run_inference():
    results = []
    answer_list = []
    for item in PROMPT_SUITE:
        pid = item["id"]
        prompt = item["prompt"]
        print(f"Running inference for {pid}")
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            top_p=TOP_P
        )
        ans_text = resp.choices[0].message.content
        results.append({
            "prompt_id": pid,
            "prompt": prompt,
            "answer": ans_text
        })
        answer_list.append(ans_text)

    # 输出完整明细
    with open("model_infer_full.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    # 输出纯答案列表，直接粘贴到打分脚本的 model_answers
    with open("model_answer_list.json", "w", encoding="utf-8") as f:
        json.dump(answer_list, f, ensure_ascii=False, indent=2)
    print("推理完成！")
    print("model_answer_list.json 内的数组可以直接填入打分脚本 model_answers")


if __name__ == "__main__":
    run_inference()