import { useState } from 'react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

export default function ContactForm({ initialData, onSubmit, onCancel }) {
    const [formData, setFormData] = useState({
        name: initialData?.name || '',
        role: initialData?.role || '',
        company: initialData?.company || '',
        email: initialData?.email || '',
        phone: initialData?.phone || '',
        website: initialData?.website || '',
        avatarUrl: initialData?.avatarUrl || '',
        tags: initialData?.tags?.join(', ') || '',
        notes: initialData?.notes || '',
    });

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        const finalData = {
            ...formData,
            tags: formData.tags.split(',').map(t => t.trim()).filter(Boolean),
        };
        onSubmit(finalData);
    };

    return (
        <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                    <Label htmlFor="name">Name*</Label>
                    <Input id="name" name="name" value={formData.name} onChange={handleChange} required />
                </div>
                <div>
                    <Label htmlFor="role">Role</Label>
                    <Input id="role" name="role" value={formData.role} onChange={handleChange} />
                </div>
                 <div>
                    <Label htmlFor="company">Company</Label>
                    <Input id="company" name="company" value={formData.company} onChange={handleChange} />
                </div>
                <div>
                    <Label htmlFor="email">Email</Label>
                    <Input id="email" name="email" type="email" value={formData.email} onChange={handleChange} />
                </div>
                 <div>
                    <Label htmlFor="phone">Phone</Label>
                    <Input id="phone" name="phone" value={formData.phone} onChange={handleChange} />
                </div>
                <div>
                    <Label htmlFor="website">Website</Label>
                    <Input id="website" name="website" type="url" value={formData.website} onChange={handleChange} />
                </div>
            </div>
             <div>
                <Label htmlFor="avatarUrl">Avatar URL</Label>
                <Input id="avatarUrl" name="avatarUrl" type="url" value={formData.avatarUrl} onChange={handleChange} />
            </div>
             <div>
                <Label htmlFor="tags">Tags (comma-separated)</Label>
                <Input id="tags" name="tags" value={formData.tags} onChange={handleChange} />
            </div>
             <div>
                <Label htmlFor="notes">Notes</Label>
                <Textarea id="notes" name="notes" value={formData.notes} onChange={handleChange} />
            </div>
            <div className="flex justify-end gap-2 pt-4">
                <Button type="button" variant="outline" onClick={onCancel}>Cancel</Button>
                <Button type="submit">Save Contact</Button>
            </div>
        </form>
    );
}