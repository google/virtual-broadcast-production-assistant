
import { Card, CardContent } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { MoreVertical, Mail, Link, Phone, Copy } from 'lucide-react';
import { toast } from 'sonner';

export default function ContactCard({ contact, onEdit, onDelete }) {
    
    const handleCopy = (text, type) => {
        navigator.clipboard.writeText(text);
        toast.success(`${type} copied to clipboard!`);
    };

    return (
        <Card className="bg-gradient-to-br from-[#1C1A22] to-[#2A2731] border-white/10 text-white overflow-hidden">
            <CardContent className="p-4">
                <div className="flex items-start justify-between">
                    <div className="flex items-start gap-4">
                        <Avatar>
                            <AvatarImage src={contact.avatarUrl} alt={contact.name} />
                            <AvatarFallback>{contact.name.charAt(0)}</AvatarFallback>
                        </Avatar>
                        <div>
                            <h3 className="font-bold text-lg">{contact.name}</h3>
                            <p className="text-sm text-[#A6A0AA]">{contact.role || 'No role specified'}</p>
                            <p className="text-sm text-[#A6A0AA]">{contact.company || 'No company'}</p>
                        </div>
                    </div>
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon" className="w-8 h-8 flex-shrink-0">
                                <MoreVertical className="w-4 h-4" />
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent>
                            <DropdownMenuItem onClick={() => onEdit(contact)}>Edit</DropdownMenuItem>
                            <DropdownMenuItem onClick={() => onDelete(contact.id)} className="text-red-500">Delete</DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>
                </div>
                
                <div className="mt-4 flex flex-wrap gap-2">
                    {contact.tags?.map(tag => (
                        <Badge key={tag} variant="outline">{tag}</Badge>
                    ))}
                </div>

                <div className="mt-4 pt-4 border-t border-white/10 flex items-center justify-start gap-2">
                    {contact.email && (
                        <a href={`mailto:${contact.email}`}><Button variant="ghost" size="icon"><Mail className="w-4 h-4" /></Button></a>
                    )}
                    {contact.website && (
                        <a href={contact.website} target="_blank" rel="noopener noreferrer"><Button variant="ghost" size="icon"><Link className="w-4 h-4" /></Button></a>
                    )}
                    {contact.phone && (
                        <Button variant="ghost" size="icon" onClick={() => handleCopy(contact.phone, 'Phone')}><Phone className="w-4 h-4" /></Button>
                    )}
                     {contact.email && (
                        <Button variant="ghost" size="icon" onClick={() => handleCopy(contact.email, 'Email')}><Copy className="w-4 h-4" /></Button>
                    )}
                </div>

            </CardContent>
        </Card>
    );
}