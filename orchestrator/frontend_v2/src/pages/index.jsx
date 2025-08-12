import Layout from "./Layout.jsx";
import Live from "./Live";
import Console from "./Console";
import Agents from "./Agents";
import Tasks from "./Tasks";
import Media from "./Media";
import Status from "./Status";
import Settings from "./Settings";
import Schedule from "./Schedule";
import Contacts from "./Contacts";
import Auth from './Auth';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { WebSocketProvider } from '@/contexts/WebSocketContext';

// Create a wrapper component that uses useLocation inside the Router context
function PagesContent() {
    return (
        <Layout>
            <Routes>
                <Route path="/" element={<Live />} />
                <Route path="/live" element={<Live />} />
                <Route path="/console" element={<Console />} />
                <Route path="/agents" element={<Agents />} />
                <Route path="/tasks" element={<Tasks />} />
                <Route path="/media" element={<Media />} />
                <Route path="/status" element={<Status />} />
                <Route path="/settings" element={<Settings />} />
                <Route path="/schedule" element={<Schedule />} />
                <Route path="/contacts" element={<Contacts />} />
            </Routes>
        </Layout>
    );
}

export default function Pages() {
    const { currentUser, loading } = useAuth();

    if (loading) {
        return <div>Loading...</div>; // Or a spinner component
    }

    return (
        <Router>
            {currentUser ? (
                <WebSocketProvider>
                    <PagesContent />
                </WebSocketProvider>
            ) : (
                <Auth />
            )}
        </Router>
    );
}