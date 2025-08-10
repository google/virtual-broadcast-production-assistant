import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import Auth from './Auth';
import Console from './Console';
import Layout from './Layout';

export default function Pages() {
    const { currentUser } = useAuth();

    return (
        <Router>
            {currentUser ? (
                <Layout currentPageName="Console">
                    <Routes>
                        <Route path="/" element={<Console />} />
                        <Route path="/console" element={<Console />} />
                    </Routes>
                </Layout>
            ) : (
                <Auth />
            )}
        </Router>
    );
}