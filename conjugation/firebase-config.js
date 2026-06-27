// Firebase v11
import { initializeApp } from "https://www.gstatic.com/firebasejs/11.9.1/firebase-app.js";
import { getDatabase } from "https://www.gstatic.com/firebasejs/11.9.1/firebase-database.js";

const firebaseConfig = {
  apiKey: "AIzaSyCfCuKEFj7xk1bUghA93wUeNfZ605i9-Po",
  authDomain: "hebrewverbs-76a3a.firebaseapp.com",
  databaseURL: "https://hebrewverbs-76a3a-default-rtdb.firebaseio.com",
  projectId: "hebrewverbs-76a3a",
  storageBucket: "hebrewverbs-76a3a.firebasestorage.app",
  messagingSenderId: "676143287803",
  appId: "1:676143287803:web:8896830fbc06a137c8cf5e"
};

const app = initializeApp(firebaseConfig);
const db = getDatabase(app);

window.firebaseApp = app;
window.firebaseDB = db;
