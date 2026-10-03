import { Navbar } from './components/layout/Navbar';
import { PageContainer } from './components/layout/PageContainer';
import { Dashboard } from './pages/Dashboard';

export function App() {
  return (
    <>
      <Navbar />
      <PageContainer>
        <Dashboard />
      </PageContainer>
    </>
  );
}

export default App;
