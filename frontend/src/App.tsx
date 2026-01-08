import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { HomePage } from './pages/HomePage';
import { MachineDetailPage } from './pages/MachineDetailPage';
import './App.css';

function App() {
  return (
    <BrowserRouter basename="/server-list">
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/machine/:machineName" element={<MachineDetailPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
