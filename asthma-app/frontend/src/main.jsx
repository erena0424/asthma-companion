import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import { AuthProvider } from './context/AuthContext.jsx';
import { CalendarProvider } from './context/CalendarContext.jsx';
import { ChatProvider } from './context/ChatContext.jsx';
import 'bootstrap/dist/css/bootstrap.min.css';
import './index.css'
import "./App.css";

createRoot(document.getElementById('root')).render(
  <AuthProvider>
    <ChatProvider>
      <CalendarProvider>
        <App />
      </CalendarProvider>
    </ChatProvider>
  </AuthProvider>

)

