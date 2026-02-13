import { Link } from "expo-router";
import { StyleSheet, Text, View } from "react-native";

export default function Index() {
  return (
    <View
      style={{
        flex: 1,
        justifyContent: "center",
        alignItems: "center",
        backgroundColor: "#323232"
      }}
    >
      <Text style={styles.title}>Edit app/index.tsx to edit this screen.</Text>
      <Link href="/about" style={styles.button}>
        Go to About screen
      </Link>
    </View>
  );

}
const styles = StyleSheet.create(
  {
    title: {
      fontSize: 30,
      fontWeight: "bold",
      textAlign: "center",
      color: "white"
    },
    button: {
      fontSize: 20,
      textDecorationLine: 'underline',
      color: '#fff',
    },
  }
)