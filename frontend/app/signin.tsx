import { useState } from "react";
import {
    View,
    Text,
    TextInput,
    TouchableOpacity,
    ActivityIndicator,
    StyleSheet,
    Alert,
    KeyboardAvoidingView,
    Platform,
    ScrollView,
    TouchableWithoutFeedback,
    Keyboard,
} from "react-native";

import { signInWithEmailAndPassword } from "firebase/auth";
import { auth } from "../lib/firebase";
import { useRouter } from "expo-router";

type Props = {

}

const SignInPage = (props: Props) => {
    const router = useRouter();

    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);


    const handleSignIn = async () => {
        if (!email || !password) {
            Alert.alert("Error", "Please enter email and password");
            return;
        }

        try {
            setLoading(true);
            await signInWithEmailAndPassword(auth, email, password);
            router.replace("/"); // redirect to home
        } catch (error: any) {
            Alert.alert("Sign In Failed", error.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <KeyboardAvoidingView
            style={{ flex: 1 }}
            behavior={Platform.OS === "ios" ? "padding" : "height"}
        >
            <TouchableWithoutFeedback onPress={Keyboard.dismiss}>
                <ScrollView
                    contentContainerStyle={{ flexGrow: 1 }}
                    keyboardShouldPersistTaps="handled"
                >
                    <View style={styles.container}>
                        <Text style={styles.title}>Sign In to your account</Text>

                        <TextInput
                            placeholder="Email"
                            value={email}
                            onChangeText={setEmail}
                            autoCapitalize="none"
                            keyboardType="email-address"
                            style={styles.input}
                        />

                        <TextInput
                            placeholder="Password"
                            value={password}
                            onChangeText={setPassword}
                            secureTextEntry
                            style={styles.input}
                        />

                        <TouchableOpacity
                            style={styles.button}
                            onPress={handleSignIn}
                            disabled={loading}
                        >
                            {loading ? (
                                <ActivityIndicator color="#fff" />
                            ) : (
                                <Text style={styles.buttonText}>Sign In</Text>
                            )}
                        </TouchableOpacity>

                        <TouchableOpacity onPress={() => router.push("/signup")}>
                            <Text style={styles.link}>
                                {`Don't have an account? Sign Up`}
                            </Text>
                        </TouchableOpacity>
                    </View>
                </ScrollView>
            </TouchableWithoutFeedback>
        </KeyboardAvoidingView>

    );
}

export default SignInPage

const styles = StyleSheet.create({
    container: {
        flex: 1,
        justifyContent: "center",
        padding: 24,
        backgroundColor: "#fff",
    },
    title: {
        fontSize: 28,
        fontWeight: "bold",
        marginBottom: 32,
        textAlign: "center",
    },
    input: {
        borderWidth: 1,
        borderColor: "#ddd",
        borderRadius: 8,
        padding: 14,
        marginBottom: 16,
    },
    button: {
        backgroundColor: "#2563eb",
        padding: 16,
        borderRadius: 8,
        alignItems: "center",
        marginTop: 8,
    },
    buttonText: {
        color: "#fff",
        fontWeight: "600",
        fontSize: 16,
    },
    link: {
        marginTop: 20,
        textAlign: "center",
        color: "#2563eb",
    },
})