import Chat from './components/Chat.jsx';
import Login from './components/Login.jsx';
import { useAuth } from './hooks/useAuth.js';

export default function App() {
  const { token, login, logout } = useAuth();

  return token ? (
    <Chat token={token} onLogout={logout} />
  ) : (
    <Login onLogin={login} />
  );
}
