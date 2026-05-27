import { BrowserRouter, Routes, Route } from 'react-router-dom';
import OnboardingPage from './pages/OnboardingPage';
import CourseResultPage from './pages/CourseResultPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<OnboardingPage />} />
        <Route path="/result" element={<CourseResultPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;