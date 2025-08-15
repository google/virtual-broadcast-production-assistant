
import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Toaster, toast } from 'sonner';
import { Button } from "@/components/ui/button";
import { Plus, Upload, Download } from 'lucide-react';
import ContactsHeader from '../components/contacts/ContactsHeader';
import ContactCard from '../components/contacts/ContactCard';
import ContactForm from '../components/contacts/ContactForm';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

const API_ENDPOINT = "/api/contacts"; // Mock endpoint

// A simple mock API for demonstration
const mockApi = {
  get: async () => {
    // To simulate API not being available, uncomment the next line
    // throw new Error("Network error");
    const localData = localStorage.getItem('contacts-storage');
    return localData ? JSON.parse(localData) : [];
  },
  post: async (contact) => {
    let contacts = await mockApi.get();
    const newContact = { ...contact, id: crypto.randomUUID(), createdAt: Date.now(), updatedAt: Date.now() };
    contacts.push(newContact);
    localStorage.setItem('contacts-storage', JSON.stringify(contacts));
    return newContact;
  },
  put: async (id, patch) => {
    let contacts = await mockApi.get();
    const index = contacts.findIndex(c => c.id === id);
    if (index === -1) throw new Error("Contact not found");
    contacts[index] = { ...contacts[index], ...patch, updatedAt: Date.now() };
    localStorage.setItem('contacts-storage', JSON.stringify(contacts));
    return contacts[index];
  },
  delete: async (id) => {
    let contacts = await mockApi.get();
    contacts = contacts.filter(c => c.id !== id);
    localStorage.setItem('contacts-storage', JSON.stringify(contacts));
    return { success: true };
  }
};


export default function ContactsPage() {
    const [contacts, setContacts] = useState([]);
    const [mode, setMode] = useState('rest'); // 'rest' or 'local'
    const [loading, setLoading] = useState(true);
    const [isFormOpen, setIsFormOpen] = useState(false);
    const [editingContact, setEditingContact] = useState(null);

    const [filters, setFilters] = useState({
        text: '',
        companies: [],
        tags: [],
        agents: [],
        sort: 'recent'
    });

    const loadContacts = useCallback(async () => {
        setLoading(true);
        try {
            const data = await mockApi.get();
            setContacts(data);
            setMode('rest');
        } catch (error) {
            console.warn("REST API failed, falling back to local storage.", error);
            const localData = localStorage.getItem('contacts-storage');
            setContacts(localData ? JSON.parse(localData) : []);
            setMode('local');
            toast.info("Contacts are stored locally. Use Import/Export to share.");
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadContacts();
    }, [loadContacts]);

    const handleSaveContact = async (contactData) => {
        try {
            if (editingContact) {
                // Update
                const updatedContact = await mockApi.put(editingContact.id, contactData);
                setContacts(prev => prev.map(c => c.id === editingContact.id ? updatedContact : c));
                toast.success("Contact updated successfully.");
            } else {
                // Create
                const newContact = await mockApi.post(contactData);
                setContacts(prev => [...prev, newContact]);
                toast.success("Contact created successfully.");
            }
            setIsFormOpen(false);
            setEditingContact(null);
        } catch (error) {
            toast.error("Failed to save contact.", { description: error.message });
        }
    };
    
    const handleDeleteContact = async (id) => {
        if (!window.confirm("Are you sure you want to delete this contact?")) return;
        try {
            await mockApi.delete(id);
            setContacts(prev => prev.filter(c => c.id !== id));
            toast.success("Contact deleted.");
        } catch(error) {
            toast.error("Failed to delete contact.", { description: error.message });
        }
    };

    const handleEditClick = (contact) => {
        setEditingContact(contact);
        setIsFormOpen(true);
    };

    const filteredAndSortedContacts = useMemo(() => {
        let result = [...contacts];

        // Filter
        if (filters.text) {
            const lowerText = filters.text.toLowerCase();
            result = result.filter(c =>
                c.name.toLowerCase().includes(lowerText) ||
                (c.role && c.role.toLowerCase().includes(lowerText)) ||
                (c.company && c.company.toLowerCase().includes(lowerText)) ||
                (c.team && c.team.toLowerCase().includes(lowerText)) ||
                (c.email && c.email.toLowerCase().includes(lowerText))
            );
        }
        
        // Sort
        if (filters.sort === 'name') {
            result.sort((a, b) => a.name.localeCompare(b.name));
        } else if (filters.sort === 'recent') {
            result.sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0));
        }

        return result;
    }, [contacts, filters]);

    const handleExport = () => {
        const dataStr = JSON.stringify(contacts, null, 2);
        const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
        
        const linkElement = document.createElement('a');
        linkElement.setAttribute('href', dataUri);
        linkElement.setAttribute('download', 'contacts.json');
        linkElement.click();
        toast.success("Contacts exported successfully.");
    };

    const handleImport = (event) => {
        const file = event.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const importedContacts = JSON.parse(e.target.result);
                if (!Array.isArray(importedContacts)) throw new Error("Invalid JSON format.");
                if(window.confirm("This will replace all current contacts. Are you sure?")) {
                    setContacts(importedContacts);
                    if(mode === 'local') {
                        localStorage.setItem('contacts-storage', JSON.stringify(importedContacts));
                    }
                    toast.success(`${importedContacts.length} contacts imported.`);
                }
            } catch (error) {
                toast.error("Failed to import contacts.", { description: error.message });
            }
        };
        reader.readAsText(file);
    };


    return (
        <div className="min-h-[calc(100vh-80px)] bg-[#0D0B12] p-4 sm:p-6 text-white">
            <Toaster richColors theme="dark" />
            <div className="max-w-7xl mx-auto">
                <ContactsHeader 
                    onAdd={() => { setEditingContact(null); setIsFormOpen(true); }}
                    onImportClick={() => document.getElementById('import-file-input').click()}
                    onExportClick={handleExport}
                    filters={filters}
                    setFilters={setFilters}
                />
                 <input id="import-file-input" type="file" accept=".json" style={{ display: 'none' }} onChange={handleImport} />

                {loading ? (
                    <div className="text-center py-10">Loading contacts...</div>
                ) : filteredAndSortedContacts.length > 0 ? (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 sm:gap-6 mt-8">
                        {filteredAndSortedContacts.map(contact => (
                            <ContactCard 
                                key={contact.id} 
                                contact={contact} 
                                onEdit={handleEditClick} 
                                onDelete={handleDeleteContact} 
                            />
                        ))}
                    </div>
                ) : (
                    <div className="text-center py-20">
                        <h3 className="text-xl font-semibold text-[#E6E1E5]">No contacts found</h3>
                        <p className="text-[#A6A0AA] mt-2">Get started by adding a new contact.</p>
                        <Button className="mt-4" onClick={() => { setEditingContact(null); setIsFormOpen(true); }}>
                            <Plus className="w-4 h-4 mr-2" /> Add Contact
                        </Button>
                    </div>
                )}
            </div>

            <Dialog open={isFormOpen} onOpenChange={setIsFormOpen}>
                <DialogContent className="bg-[#1C1A22] border-white/10 text-white max-w-2xl w-[95vw] sm:w-full">
                    <DialogHeader>
                        <DialogTitle>{editingContact ? 'Edit Contact' : 'Add New Contact'}</DialogTitle>
                    </DialogHeader>
                    <ContactForm 
                        initialData={editingContact} 
                        onSubmit={handleSaveContact} 
                        onCancel={() => setIsFormOpen(false)} 
                    />
                </DialogContent>
            </Dialog>
        </div>
    );
}
