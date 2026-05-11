import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { getLists } from "@/api/contacts";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

const limit = 20;

export function ListsPage() {
  const [offset, setOffset] = useState(0);
  const lists = useQuery({ queryKey: ["lists", limit, offset], queryFn: () => getLists(limit, offset) });
  const total = lists.data?.total ?? 0;
  return (
    <section className="grid gap-5">
      <div>
        <h2 className="text-2xl font-semibold tracking-normal">Lists</h2>
        <p className="text-sm text-muted-foreground">Audience lists from the backend.</p>
      </div>
      <Card>
        <CardContent className="p-0">
          {lists.isLoading ? (
            <div className="grid gap-2 p-5">{Array.from({ length: 5 }, (_, index) => <Skeleton key={index} className="h-12 w-full" />)}</div>
          ) : lists.data?.items.length ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Contacts</TableHead>
                  <TableHead>Tags</TableHead>
                  <TableHead>Created</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {lists.data.items.map((list) => (
                  <TableRow key={list.id}>
                    <TableCell className="font-medium">{list.name}</TableCell>
                    <TableCell>{list.contact_count}</TableCell>
                    <TableCell className="flex gap-1">{list.tags.map((tag) => <Badge key={tag} variant="outline">{tag}</Badge>)}</TableCell>
                    <TableCell>{new Date(list.created_at).toLocaleDateString()}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="p-8 text-center text-sm text-muted-foreground">No lists found.</div>
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
