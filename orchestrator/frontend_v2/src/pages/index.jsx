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

import { BrowserRouter as Router, Route, Routes, useLocation } from 'react-router-dom';

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
                
                
                <Route path="/Live" element={<Live />} />
                
                <Route path="/Console" element={<Console />} />
                
                <Route path="/Agents" element={<Agents />} />
                
                <Route path="/Tasks" element={<Tasks />} />
                
                <Route path="/Media" element={<Media />} />
                
                <Route path="/Status" element={<Status />} />
                
                <Route path="/Settings" element={<Settings />} />
                
                <Route path="/Schedule" element={<Schedule />} />
                
                <Route path="/Contacts" element={<Contacts />} />
                
            </Routes>
        </Layout>
    );
}

export default function Pages() {
    return (
        <Router>
            <PagesContent />
        </Router>
    );
}