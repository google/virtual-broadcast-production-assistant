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
import { BrowserRouter as Router, Route, Routes, useLocation } from 'react-router-dom';
import { useAuth } from '@/contexts/useAuth';

const PAGES = {
    Live: Live,
    Console: Console,
    Agents: Agents,
    Tasks: Tasks,
    Media: Media,
    Status: Status,
    Settings: Settings,
    Schedule: Schedule,
    Contacts: Contacts,
}

function _getCurrentPage(url) {
    if (url.endsWith('/')) {
        url = url.slice(0, -1);
    }
    let urlLastPart = url.split('/').pop();
    if (urlLastPart.includes('?')) {
        urlLastPart = urlLastPart.split('?')[0];
    }

    const pageName = Object.keys(PAGES).find(page => page.toLowerCase() === urlLastPart.toLowerCase());
    return pageName || Object.keys(PAGES)[0];
}

// Create a wrapper component that uses useLocation inside the Router context
function PagesContent() {
    const location = useLocation();
    const currentPage = _getCurrentPage(location.pathname);

    return (
        <Layout currentPageName={currentPage}>
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
    const { currentUser, loading, isUpgrading } = useAuth();

    if (loading) {
        return <div>Loading...</div>; // Or a spinner component
    }

    if (isUpgrading) {
        return <Auth />;
    }

    return (
        <Router>
            {currentUser ? <PagesContent /> : <Auth />}
        </Router>
    );
}