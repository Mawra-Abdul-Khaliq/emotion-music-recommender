# 🎵 Emotion-Based Music Recommendation System

This project is an intelligent music recommendation system that uses **facial expression recognition** to suggest songs aligned with a user’s current emotional state. It combines **computer vision**, **machine learning**, and **web development** to deliver a personalized and engaging music experience.

## 🧠 How It Works

1. The webcam captures the user's facial expression in real time.
2. A trained **Convolutional Neural Network (CNN)** processes the image to classify the emotion (e.g., happy, sad, angry, surprised, neutral).
3. Based on the detected emotion, the system selects and plays a suitable song from a predefined playlist.
4. All interaction is handled through a simple, user-friendly **Flask web interface**.

## 🚀 Features

- 🎥 Real-time emotion detection via webcam
- 🤖 CNN-based facial expression classification
- 🎶 Music recommendation tailored to mood
- 🌐 Lightweight and interactive Flask web interface
- 🔐 Camera access control managed through user sessions

## 🛠️ Tech Stack

- **Python 3**
- **OpenCV** – for image capture and preprocessing
- **TensorFlow/Keras** – for the CNN emotion detection model
- **Flask** – web application framework
- **HTML/CSS/JavaScript** – frontend
- **SQLite/MySQL** – user preference and session management

## 📂 Project Structure

