import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { HomePage } from './pages/HomePage';
import { MachineDetailPage } from './pages/MachineDetailPage';
import { UPSPage } from './pages/UPSPage';
import './App.css';

function App() {
  return (
    <BrowserRouter basename="/server-list">
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/machine/:machineName" element={<MachineDetailPage />} />
        <Route path="/ups" element={<UPSPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
