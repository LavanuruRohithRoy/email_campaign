import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";

import { getContacts } from "@/api/contacts";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { ContactStatus } from "@/types/api";

const limit = 20;

export function ContactsPage() {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<ContactStatus | "all">("all");
  const [offset, setOffset] = useState(0);
  const query = useMemo(() => ({ search, status, limit, offset }), [search, status, offset]);
  const contacts = useQuery({ queryKey: ["contacts", query], queryFn: () => getContacts(query) });
  const total = contacts.data?.total ?? 0;

  return (
    <section className="grid gap-5">
      <div>
        <h2 className="text-2xl font-semibold tracking-normal">Contacts</h2>
        <p className="text-sm text-muted-foreground">Search, filter, and inspect subscriber status.</p>
      </div>
      <div className="flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
          <Input className="pl-9" placeholder="Search contacts" value={search} onChange={(event) => { setSearch(event.target.value); setOffset(0); }} />
        </div>
        <Select value={status} onValueChange={(value) => { setStatus(value as ContactStatus | "all"); setOffset(0); }}>
          <SelectTrigger className="sm:w-48">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {["all", "active", "unsubscribed", "bounced", "complained"].map((item) => (
              <SelectItem key={item} value={item}>
                {item}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <Card>
        <CardContent className="p-0">
          {contacts.isLoading ? (
            <div className="grid gap-2 p-5">{Array.from({ length: 6 }, (_, index) => <Skeleton key={index} className="h-12 w-full" />)}</div>
          ) : contacts.data?.items.length ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Email</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {contacts.data.items.map((contact) => (
                  <TableRow key={contact.id}>
                    <TableCell className="font-medium">{contact.email}</TableCell>
                    <TableCell>{[contact.first_name, contact.last_name].filter(Boolean).join(" ") || "-"}</TableCell>
                    <TableCell><Badge variant={contact.status === "active" ? "default" : "outline"}>{contact.status}</Badge></TableCell>
                    <TableCell>{new Date(contact.created_at).toLocaleDateString()}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="p-8 text-center text-sm text-muted-foreground">No contacts found.</div>
          )}
        </CardContent>
      </Card>
      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <span>{total} total</span>
        <div className="flex gap-2">
          <Button variant="outline" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - limit))}>Previous</Button>
          <Button variant="outline" disabled={offset + limit >= total} onClick={() => setOffset(offset + limit)}>Next</Button>
        </div>
      </div>
    </section>
  );
}
