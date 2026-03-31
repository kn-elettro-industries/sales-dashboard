import { redirect } from "next/navigation";

/** Distributor vs Target is temporarily hidden; keep URL stable for bookmarks. */
export default function DistributorPage() {
    redirect("/reports");
}
