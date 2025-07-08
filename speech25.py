import os
import subprocess
import sys
# List of required packages
REQUIRED_PACKAGES = ["keyboard", "requests", "beautifulsoup4", "pyttsx3", "speechrecognition", "pyaudio"]

# Marker file to indicate installation has been completed
MARKER_FILE = "deps_installed.txt"

def install_dependencies():
    """Installs missing dependencies."""
    for package in REQUIRED_PACKAGES:
        subprocess.run([sys.executable, "-m", "pip", "install", package], check=True)

def check_and_install():
    """Check for marker file and install dependencies if needed."""
    if not os.path.exists(MARKER_FILE):
        print("Installing dependencies...")
        install_dependencies()
        with open(MARKER_FILE, "w") as f:
            f.write("Dependencies installed.\n")
        print("Installation complete. Marker file created.")
    else:
        print("All dependencies are already installed.")

# Run the check
check_and_install()


import requests
from bs4 import BeautifulSoup
import pyttsx3
import speech_recognition as sr
import time
import talkmod
import re
import keyboard
import ollamamodel
from datetime import datetime
import threading
conversation_history = []



global model
global current_date
global current_time
global memory

def load_conversation_history():
    """Loads the previous conversation history from a file."""
    try:
        if os.path.exists("conversation_history.txt"):
            with open(f"conversation_history.txt", 'r') as file:
                return file.read()
        else:
            print("No previous conversation history found.")
            return ""
    except Exception as e:
        print(f"Error loading conversation history: {e}")
        return "Failed to load the conversation history."

def save_conversation_history():
    """Saves the current conversation history to a file."""
    try:
        with open("conversation_history.txt", 'a') as file:
            # Convert each item in conversation_history to string
            content = "\n model = {model}\n{current_date}\n{current_time}\n".join(str(item) for item in conversation_history)
            file.write(content)
        print("Conversation history saved.")
    except Exception as e:
        print(f"Error saving conversation history: {e}")


def recognize_speech_from_mic():
    """Recognizes speech from the microphone."""
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        try:
            audio = recognizer.listen(source)
            user_input = recognizer.recognize_google(audio, language='en-US')
            return user_input
        except sr.UnknownValueError:
            print("Google Speech Recognition could not understand audio.")
        except sr.RequestError as e:
            print(f"Could not request results from Google Speech Recognition service; {e}")
    return None


engine = pyttsx3.init()
engine.setProperty('rate', 150)  # Speech rate
engine.setProperty('volume', 0.7)  # Volume level

stop_speaking_flag = threading.Event()

def speak(text):
    """Speaks the given text and stops if the space bar is pressed."""
    stop_speaking_flag.clear()  # Reset the flag before speaking

    def stop_on_space(event):
        """Stops speaking when the space bar is pressed."""
        if event.name == "space":  # Check if the pressed key is 'space'
            stop_speaking()

    keyboard.on_press(stop_on_space)  # Listen for space bar press

    def run_speech():
        """Runs speech synthesis."""
        global engine
        try:
            engine.say(text)
            engine.runAndWait()
        except RuntimeError as e:
            print("Speech Error:", str(e))
        finally:
            stop_speaking_flag.clear()
            keyboard.unhook_all()  # Remove key listener after speech ends

    speech_thread = threading.Thread(target=run_speech, daemon=True)
    speech_thread.start()

def stop_speaking():
    """Stops speaking immediately."""
    stop_speaking_flag.set()
    engine.stop()
    keyboard.unhook_all()  # Ensure key listener is removed


def show_help():
    """Displays the help menu."""
    help_text = """
    Available Commands:
    - Search for [query]: Perform a web search.
    - What's the time/date: Get the current time or date.
    - Run [command]: Execute a system command.
    - Kill [process]: Terminate a running process.
    - Stop: Stop speaking immediately.
    - Exit/Quit/Goodbye: End the interaction.
    """
    print(help_text)
    
def read_file(filepath):
    """Reads the content of a file."""
    try:
        with open(filepath, 'r') as file:
            return file.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        save_conversation_history(f"Error reading file; {e}")
        return "Failed to read the file."

def write_file(filepath, content):
    """Writes content to a file."""
    try:
        with open(filepath, 'a') as file:
            file.write(content)
        return f"Successfully wrote to {filepath}."
    except Exception as e:
        conversation_history.append(f"{current_date}{current_time}Failed to write to {filepath}: {e}")
        return f"Failed to write to {filepath}: {e}"

def fetch_web_content(url):
    """Fetches the web content from a given URL."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        return str(soup)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching web content: {e}")
        return ""


def clean_web_content(text):
    """Remove HTML tags, CSS selectors, and JavaScript from web scraped data."""
    # Create a BeautifulSoup object to parse the text
    soup = BeautifulSoup(text, 'html.parser')
    
    # Remove all script tags
    for script in soup(["script", "style"]):
        script.decompose()
    
    # Extract only text within <div>, <span>, and <p> tags
    filtered_text = []
    for tag in soup(['div', 'span', 'p']):
        filtered_text.append(tag.get_text(strip=True))
    
    # Join all the extracted texts into a single string
    cleaned_text = ' '.join(filtered_text)
    
    return cleaned_text.strip()

def summarize_web_content(text):
    """Summarizes the given text."""
    try:
        text = clean_web_content(text)
        return query_ollama_clean(f"SUMMARIZE: {text}")   # Ask Ollama to summarize the text
    except Exception as e:
        print(f"Error summarizing text: {e}")
        return "Failed to summarize the text."

def extract_code_from_response(response):
    """Extracts code blocks from Ollama's response, supporting multiple languages."""
    if not response:
        print("Error: Ollama API returned an empty response.")
        conversation_history.append({"user": "Extracting code failed", "ollama": "Ollama API returned an empty response"})
        return None

    try:
        # Extract all code blocks from the response
        code_blocks = re.findall(r"```(.*?)```", response, flags=re.DOTALL)
        if not code_blocks or len(code_blocks) != 1:
            print("Failed to extract valid code from Ollama's response. Response is not in the expected format.")
            conversation_history.append({"user": "Extracting code failed", "ollama": "Failed to parse response"})
            return None
        extracted_code = code_blocks[0].strip()

        # Detect language prefix (e.g., python, sh, cpp, ruby, etc.) and remove it
        lines = extracted_code.split('\n')
        first_line = lines[0].strip().lower()
        
        # List of common language prefixes
        language_prefixes = {"python", "sh", "bash", "cmd", "cpp", "c++", "ruby", "javascript", "java", "go", "rust"}
        
        if first_line in language_prefixes:
            extracted_code = '\n'.join(lines[1:])
        
        return extracted_code.strip()
    except Exception as e:
        print(f"Error: Failed to extract code from Ollama's response. {e}")
        conversation_history.append({"user": "Extracting code failed", "ollama": str(e)})
        return None


def execute_system_command(commands):
    """Execute the given commands in separate shell processes."""
    
    # Convert single command to a list if necessary
    if not isinstance(commands, list):
        commands = [commands]
    
    for command in commands:
        try:
            subprocess.Popen(command, shell=True)
            print(f"Command '{command}' executed successfully.")
            conversation_history.append({"System": f"Executed command: {command}", "Status": "Command executed successfully"})
        except subprocess.CalledProcessError as e:
            print(f"Failed to execute command '{command}': {e}")
            conversation_history.append({"System": f"Executed command: {command}", "Status": f"Failed to execute command: {e}"})
    return None

def process_ollama_response(response):
    """Process Ollama's response and execute any code blocks."""
    try:
        # Extract URLs from the response
        urls = re.findall(r'https?://[^\s]+', response)
        if urls:
            for url in urls:
                print(f"Fetched content from {url}")
                web_content = fetch_web_content(url)
                print(web_content)
                summarized_content = query_ollama(f"SUMMARIZE: {web_content}")
                conversation_history.append(f"Summarized content from {url}:")
                conversation_history.append(f"{summarized_content}")
                print(summarized_content)
                speak(summarized_content)

        # Extract and execute code blocks
        extracted_code = extract_code_from_response(response)
        if extracted_code:
            print(f"Extracting command: {extracted_code}")
            result = execute_system_command(extracted_code)
            if result:
                conversation_history.append({"user": "Executed command", "ollama": f"Command executed with result: {result}"})
        else:
            conversation_history.append({"user": "No code extracted", "ollama": "No valid code block found in response"})
        print(response)    
    except Exception as e:
        error_message = f"An unexpected error occurred during processing. Details: {str(e)}"
        print(error_message)
        conversation_history.append(f"An error occurred: {error_message}")
        save_conversation_history()
    
    return None

def refine_memory():

    def write_memory_file(filepath, content):
        """Writes content to a file."""
        try:
            with open(filepath, 'a') as file:
                file.write(content)
            return f"Successfully wrote to {filepath}."
        except Exception as e:
            conversation_history.append(f"{current_date}{current_time}Failed to write to {filepath}: {e}")
            return f"Failed to write to {filepath}: {e}"
    file = read_file("conversation_history.txt")
    print("History loaded")
    
    current_memory = read_file("memory.txt")
    print("Memory loaded")
    print("Reading converstation_history.txt\nReading memory.txt\nSending to be organized.")
    memory = query_ollama_clean(f"""Analyze the conversation history and extract key details that contribute to successful outcomes.  
        Retain previously stored memory while integrating newly found critical information.  
        Structure the memory in a way that is clear and efficient for LLMs to process, ensuring continuity in understanding and execution.  

        - Keep all previously stored memory intact.  
        - Extract important successes from the conversation history.  
        - Store details in a structured format that improves recall and decision-making.  

        Conversational History:
        {file}

        Current Memory:
        {current_memory}
        """)
    print(memory)
    print("Finished Sumarization of Conversation and added to memory.txt")
    write_memory_file("memory.txt", memory)


def query_ollama_clean(prompt):
    
    try:
        data = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "n_predict": 500,
            "temperature": 0.7,
            "top_p": 0.9,
            "options": {
                "num_ctx": 12096
            }
        }
        OLLAMA_URL = "http://localhost:11434/api"
        response = requests.post(f"{OLLAMA_URL}/generate", json=data)
        response.raise_for_status()
        print(response)
        return response.json().get("response", "I have no response at the moment.")
    except requests.exceptions.RequestException as e:
        print(f"Error communicating with SYSTEM: {e}")
        return "I'm having trouble connecting to Ollama."
        


def query_ollama(prompt):
    """Sends a prompt to Ollama and returns the response."""
    current_memory = read_file("memory.txt")
    conversation_history_str = load_conversation_history()
    try:
        full_prompt = f"""
        Conversation History: {conversation_history}

        Here is a catalog of successfully attempts stored in memory that you can recal on to help with completeing tasks if needed. 
            
        Memory Catalog: {current_memory}

        Please retain and be concise and answer in the format that follows. 
            What you just received in order:
                1-Conversation History. A log of the converstaion with the user.
                2-Memory Catalog. A log of successful attempts and stuff stored for training. 
            what your going to receive in order:
                1-User Task: the task the user wants you to complete. 
                2-Reponse Format: instruction on how to respond to the user to complete the task.

        User Task: {prompt}
            
        Response Format:
            Ollama System Command & Execution Agent

        Role Overview: You are an AI assistant with full access to execute system commands, perform file operations, interact with Windows and Linux systems, and conduct web searches. Your responses will be processed and executed directly, so it is crucial to follow the strict formatting guidelines precisely to ensure accurate execution.

        System Command Execution: You can execute any system command or program, including running processes, terminating them, and modifying files on both Windows and Linux systems.

            All commands must be formatted exactly as follows:
            Windows Command:
            cmd
            ```            
            command_here
            ```
            Linux Command:
            bash
            ```
            command_here
            ```
            Example (Windows command):
            cmd
            ```
            ping google.com
            ```
            Example (Linux command):
            bash
            ```
            ping google.com
            ```
            File Operations:
            Retrieve a list of files:
            cmd            
            ```
            dir
            ```
            Read a file's contents:
            cmd
            ```
            type filename.txt
            ```
            Write content to a file:
            c
            ```
            echo Hello > filename.txt;
            ```
            List available system commands:
            cmd
            ```
            help
            ```
            Web Searching: If user says search for ...? or If a query requires information retrieval, return a direct search URL for the query to enable automated web scraping and execution. Example search URL.

            https://www.google.com/search?q=[your_query_here]
            
            Code Execution: Any code you generate must be enclosed in the following format:
            code
            ```
            generated_code_here
            ```

            Example:
            code            
            ```
            print("Hello, world!");
            ```
        Conversation History & Context Awareness: Maintain awareness of prior interactions to ensure relevant responses. to aid in generation of code and to remind the user of maybe things they forgot about or if the user set a reminder. 

        Response Guidelines:

            Always format system commands or code using the strict triple-backtick guidelines provided above.
            For web searches, provide direct search URLs without additional explanation.
            If executing code, ensure that it is enclosed in the proper format for execution.
            Send back all commands needed for task at once. Each command separated by semicolon ;. 
        
            """
        
        data = {
            "model": model,
            "prompt": full_prompt,
            "stream": False,
            "n_predict": 250,
            "temperature": 0.5,
            "top_p": 0.9,
            "options": {
                "num_ctx": 12096
            }
        }
        OLLAMA_URL = "http://localhost:11434/api"
        response = requests.post(f"{OLLAMA_URL}/generate", json=data)
        response.raise_for_status()
        print(response)

        
        return response.json().get("response", "I have no response at the moment.")
    except requests.exceptions.RequestException as e:
        print(f"Error communicating with SYSTEM: {e}")
        return "I'm having trouble connecting to Ollama."




def basefunctions(user_input):

    #Here you can extend off the model and do simple worded call commands to execute functions.
    #This is where you would add things like turn of the lights or check my email. 

    # Handle exit commands
    if user_input.lower() in ["exit", "quit", "goodbye"]:
        print("Goodbye!")
        speak("Goodbye!")
        save_conversation_history()
        exit()

    # Handle 'stop' command
    elif user_input.lower() == "stop":
        stop_speaking()
        print("Stop command received. Speech stopped.")
    
    # Handle help command
    elif user_input.lower() == "show help":
        show_help()
        next 
    
    # Handle time commands
    elif user_input.lower() in ["what's the time", "what time is it"]:
        current_time = time.strftime("%I:%M %p")
        print(f"The time is {current_time}.")
        speak(f"The time is {current_time}.")
        next
    elif user_input.lower() in ["what's the date", "what date is it"]:
        current_date = datetime.now().strftime("%Y-%m-%d")
        print(f"Today's date is {current_date}.")
        speak(f"Today's date is {current_date}.")
        next
    elif user_input.lower() in ["find", "look for", "where is"]:
        execute_command(query_ollama("send back dir command with file name {user_input} to search for to be read."))
    return user_input
    
def menu():

    count = 0
    while count < 5:
        os.system("cls")

        if keyboard.is_pressed("f5"):
            print("Continuing...")
            break  # Exit the loop when F5 is pressed
        
        elif keyboard.is_pressed("f7"):
            print("Organizing Thoughts...")
            refine_memory()
            break  # Exit the loop when F7 is pressed
        print(f"""Press F5 to continue or F7 to Update Memory from conversation history.\n
            {count} Seconds Remaining""")
        time.sleep(1)
        count += 1


def main():
    try:
        ollama_response = ""
        while True:
            # Initialize current_date and current_time
            global current_date, current_time
            current_date = datetime.now().strftime("%Y-%m-%d")
            current_time = time.strftime("%I:%M %p")
 
            # Get user input

            user_input = talkmod.record_and_transcribe()
            basefunctions(user_input)
            print(f"You said: {user_input}")
            conversation_history.append(f"User: {user_input}")

            # Process Ollama response
            ollama_response = query_ollama(user_input)
            
            try:
                process_ollama_response(ollama_response)
                try:
                    stripped_response = re.sub(r'```([\s\S]*?)```', '', ollama_response)
                    conversation_history.append(f"SYSTEM: {stripped_response}")
                    print(stripped_response)
                    

                except Exception as e:
                    print(f"Error processing response: {e}")
                    conversation_history.append(f"Error processing response: {e}")
                    user_input = user_input + e
            except Exception as e:
                error_message = f"An unexpected error occurred during processing. Details: {e}"
                print(error_message)
                conversation_history.append(f"An error occurred: {error_message}")
                user_input = user_input + error_message
                
            save_conversation_history()
        while e or error_message:
            
            ollama_response = query_ollama(f"Results of code sent please resolve: {user_input}")
            
            try:
                process_ollama_response(ollama_response)
                try:
                    stripped_response = re.sub(r'```([\s\S]*?)```', '', ollama_response)
                    conversation_history.append(f"SYSTEM: {stripped_response}")
                    print(stripped_response)
                    

                except Exception as e:
                    print(f"Error processing response: {e}")
                    conversation_history.append(f"Error processing response: {e}")
                    user_input = user_input + e
            except Exception as e:
                error_message = f"An unexpected error occurred during processing. Details: {e}"
                print(error_message)
                conversation_history.append(f"An error occurred: {error_message}")
                user_input = user_input + error_message
                save_conversation_history()

    except KeyboardInterrupt:
        print("\nExiting. Goodbye!")
        speak("Goodbye!")
        save_conversation_history()

if __name__ == "__main__":

    model = ollamamodel.get_ollama_model_http()
    menu()
    print("Welcome to Voice Interaction with Ollama!")
    speak("Welcome back, Sir!")
    main()
    save_conversation_history()
