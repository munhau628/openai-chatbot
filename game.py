import os
import streamlit as st
from dotenv import load_dotenv
import google.generativeai as genai
from typing import List, Dict, Any
import random

# Load environment variables and configure API
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Custom styles
def apply_custom_styles():
    st.markdown("""
        <style>
        .stButton button {
            width: 100%;
            border-radius: 5px;
            margin: 2px;
            padding: 10px;
            font-size: 16px;
        }
        .story-text {
            background-color: rgba(255, 255, 255, 0.1);
            padding: 20px;
            border-radius: 10px;
            margin: 10px 0;
        }
        </style>
    """, unsafe_allow_html=True)

def initialize_session_state():
    """Initialize or reset session state variables"""
    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = []
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "game_state" not in st.session_state:
        st.session_state.game_state = {
            "health": 100,
            "food": 5,  # Starting food supply
            "choices_made": 0,
            "success": False,
            "mode": None,  # Easy, Hard, or Nightmare mode
            "ended": False  # To track if the game has ended
        }
    if "language" not in st.session_state:
        st.session_state.language = "English"

def create_model() -> genai.GenerativeModel:
    """Create and configure the Gemini model"""
    generation_config = {
        "temperature": 0.8,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 512,
        "response_mime_type": "text/plain",
    }
    
    return genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config=generation_config
    )

def generate_story_response(conversation_history: List[Dict[str, Any]]) -> str:
    """Generate the next part of the story using the Gemini model"""
    try:
        model = create_model()
        chat_session = model.start_chat(history=conversation_history)
        
        # Add context about game state to the prompt
        context = f"""
        Current game state:
        - Mode: {st.session_state.game_state['mode']}
        - Health: {st.session_state.game_state['health']}
        - Food: {st.session_state.game_state['food']}
        - Choices made: {st.session_state.game_state['choices_made']}
        - Success: {"yes" if st.session_state.game_state['success'] else "no"}
        
        In Easy mode:
        - Higher chance of positive outcomes
        - Easier access to food
        - Health restoration available through events
        
        In Hard mode:
        - Food is scarce, and only food can restore health
        - Balanced good and bad outcomes
        
        In Nightmare mode:
        - Food is extremely scarce and does not restore health
        - Negative outcomes are more frequent than positive outcomes
        - Health can only be lost, not restored
        """
        
        # Get response from model
        response = chat_session.send_message(
            conversation_history[-1]["parts"][0]["text"] + "\n" + context
        )
        
        return response.text
    except Exception as e:
        st.error(f"Error generating response: {str(e)}")
        return "Something went wrong in the forest... Please try again."

def update_game_state(response_text: str):
    """Update game state based on the story response with varying outcomes based on mode"""
    if st.session_state.game_state['mode'] == "Nightmare":
        food_restore_health = 0
    else:
        food_restore_health = 10
    
    # Consume food with each choice
    if st.session_state.game_state['food'] > 0:
        st.session_state.game_state['food'] -= 1
        new_health = min(100, st.session_state.game_state['health'] + food_restore_health)
        if new_health > st.session_state.game_state['health']:
            st.session_state.game_state['health'] = new_health
            if food_restore_health > 0:
                st.info(f"🍞 You consumed food and restored {food_restore_health} health points!")
    else:
        st.session_state.game_state['health'] -= 10

    # Determine outcome weights based on mode
    if st.session_state.game_state['mode'] == "Easy":
        outcome = random.choices(['good', 'bad'], weights=[0.7, 0.3])[0]
        food_chance = 0.8  # Increased food gathering rate
    elif st.session_state.game_state['mode'] == "Hard":
        outcome = random.choices(['good', 'bad'], weights=[0.5, 0.5])[0]
        food_chance = 0.4  # Increased food gathering rate
    elif st.session_state.game_state['mode'] == "Nightmare":
        outcome = random.choices(['good', 'bad'], weights=[0.3, 0.7])[0]
        food_chance = 0.2  # Increased food gathering rate
    else:
        outcome = 'good'
        food_chance = 0.0

    # Define responses for each outcome type
    if outcome == 'good':
        if "move closer to success" in response_text.lower():
            st.session_state.game_state['success'] = True
        elif st.session_state.game_state['mode'] == "Easy" and "restore health" in response_text.lower():
            st.session_state.game_state['health'] = min(100, st.session_state.game_state['health'] + 20)

        # Chance to find food supply in both modes
        if random.random() < food_chance:
            st.session_state.game_state['food'] += 3
            st.info("🍞 You found some food supplies!")

    elif outcome == 'bad':
        if "lose health" in response_text.lower():
            st.session_state.game_state['health'] -= 10
        elif "fatal event" in response_text.lower() and st.session_state.game_state['health'] <= 10:
            st.session_state.game_state['health'] = 0
    
    # Check if game should end
    if st.session_state.game_state['success']:
        st.session_state.game_state['ended'] = True
    elif st.session_state.game_state['health'] <= 0:
        st.session_state.game_state['ended'] = True
    
    # Increment choices counter
    st.session_state.game_state['choices_made'] += 1

def display_game_state():
    """Display the current game state in the sidebar"""
    st.sidebar.header("Game Status")
    
    # Health bar
    st.sidebar.progress(st.session_state.game_state['health'] / 100)
    st.sidebar.write(f"Health: {st.session_state.game_state['health']}%")
    
    # Food supply
    st.sidebar.subheader("Food Supply")
    st.sidebar.write(f"Food remaining: {st.session_state.game_state['food']}")
    
    # Choices made and success status
    st.sidebar.write(f"Choices made: {st.session_state.game_state['choices_made']}")
    if st.session_state.game_state['success']:
        st.sidebar.write("Success: 🌟 Close to escaping the forest!")

def main():
    st.set_page_config(page_title="The Cursed Forest", layout="wide")
    apply_custom_styles()
    
    st.title("🌲 The Cursed Forest - Interactive Adventure")
    
    # Initialize session state
    initialize_session_state()
    
    # Add restart button in sidebar
    if st.sidebar.button("Restart Game"):
        st.session_state.clear()
        initialize_session_state()
    
    # Language selection
    st.sidebar.subheader("Language")
    if st.sidebar.button("English"):
        st.session_state.language = "English"
    if st.sidebar.button("中文"):
        st.session_state.language = "Chinese"
    
    # Set language-specific texts
    if st.session_state.language == "English":
        greeting_text = "Welcome, brave soul! You are Kaelen, a wanderer who finds yourself lost in the mysterious Cursed Forest."
        instruction_text = "What would you like to do?\n\nRemember, you can type commands like 'explore', 'look around', 'rest', or any other action you can think of. Good luck!"
        restart_text = "Restart Game"
        success_text = "🎉 Congratulations! You have successfully escaped the Cursed Forest!"
        game_over_text = "💀 Game Over - You have perished in the Cursed Forest"
        next_action_text = "What will you do next?"
        mode_selection_text = "Choose your difficulty mode:"
        easy_mode_text = "Easy Mode"
        hard_mode_text = "Hard Mode"
        nightmare_mode_text = "Nightmare Mode"
    else:
        greeting_text = "欢迎，勇敢的灵魂！你是凯伦，一位在神秘的诅咒森林中迷失的流浪者。"
        instruction_text = "你想做什么？\n\n记住，你可以输入像 '探索'，'环顾四周'，'休息' 等命令，或任何你能想到的行动。祝你好运！"
        restart_text = "重新开始"
        success_text = "🎉 恭喜！你成功逃离了诅咒森林！"
        game_over_text = "💀 游戏结束 - 你在诅咒森林中牺牲了"
        next_action_text = "接下来你要做什么？"
        mode_selection_text = "选择你的难度模式："
        easy_mode_text = "简单模式"
        hard_mode_text = "困难模式"
        nightmare_mode_text = "噩梦模式"
    
    # Mode selection if starting new game
    if st.session_state.game_state["mode"] is None:
        st.write(mode_selection_text)
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button(easy_mode_text):
                st.session_state.game_state["mode"] = "Easy"
        with col2:
            if st.button(hard_mode_text):
                st.session_state.game_state["mode"] = "Hard"
        with col3:
            if st.button(nightmare_mode_text):
                st.session_state.game_state["mode"] = "Nightmare"
        return  # Wait for user to select mode before continuing
    
    # Introduction message if starting new game
    if not st.session_state.conversation_history:
        intro_message = {
            "role": "model",
            "parts": [{
                "text": (
                    f"{greeting_text} "
                    f"{instruction_text}"
                )}]
        }
        st.session_state.conversation_history.append(intro_message)
        st.session_state.messages.append(intro_message)
    
    # Display game state in sidebar
    display_game_state()
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message("assistant" if message["role"] == "model" else "user"):
            st.markdown(message["parts"][0]["text"])
    
    # Game over check
    if st.session_state.game_state['ended']:
        if st.session_state.game_state['success']:
            st.success(success_text)
        else:
            st.error(game_over_text)
        if st.button(restart_text):
            st.session_state.clear()
            initialize_session_state()
        return
    
    # User input
    user_input = st.chat_input(next_action_text, key="user_input")
    
    if user_input:
        # Add user input to history
        user_message = {"role": "user", "parts": [{"text": user_input}]}
        st.session_state.conversation_history.append(user_message)
        st.session_state.messages.append(user_message)
        
        with st.spinner("The forest whispers..."):
            # Generate and display response
            response = generate_story_response(st.session_state.conversation_history)
            
            # Update game state based on response
            update_game_state(response)
            
            # Add response to history
            ai_message = {"role": "model", "parts": [{"text": response}]}
            st.session_state.conversation_history.append(ai_message)
            st.session_state.messages.append(ai_message)
            
            # Display response
            with st.chat_message("assistant"):
                st.markdown(response)

if __name__ == "__main__":
    main()
