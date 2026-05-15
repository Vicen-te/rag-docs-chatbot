import { useState } from 'react';

import { login as loginApi } from '../api/client.js';

export default function Login({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const data = await loginApi(username, password);
      onLogin(data.access);
    } catch {
      setError('Invalid credentials.');
    }
  };

  return (
    <form className="login" onSubmit={submit}>
      <h1>rag-docs-chatbot</h1>
      <input
        placeholder="username"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        autoFocus
      />
      <input
        placeholder="password"
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />
      <button type="submit">Login</button>
      {error && <div className="error">{error}</div>}
    </form>
  );
}
