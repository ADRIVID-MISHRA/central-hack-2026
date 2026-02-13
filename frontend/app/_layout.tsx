import { auth } from "@/lib/firebase";
import { Stack, useRouter } from "expo-router";
import { onAuthStateChanged } from "firebase/auth";
import { useEffect, useState } from "react";

export default function RootLayout() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      if (user) {
        router.replace("/"); // go to home (index.tsx)
      } else {
        router.replace("/signin"); // or your signin page
      }
      setLoading(false);
    });

    return unsubscribe;
  }, []);

  return (
    <Stack>
      <Stack.Screen name="index" options={{ title: 'Home' }} />
      <Stack.Screen name="about" options={{ title: 'About' }} />
    </Stack>
  );
}
