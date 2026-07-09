import java.util.*;

class Node {
    int data;
    Node next;

    Node(int val) {
        data = val;
        next = null;
    }
}

public class Main {

    // Insert node at end
    static Node insertNode(Node head, int val) {
        Node newNode = new Node(val);

        if (head == null) {
            return newNode;
        }

        Node temp = head;

        while (temp.next != null) {
            temp = temp.next;
        }

        temp.next = newNode;

        return head;
    }

    // Display linked list
    static void display(Node head) {
        Node temp = head;

        while (temp != null) {
            System.out.print(temp.data + " -> ");
            temp = temp.next;
        }

        System.out.println("null");
    }

    // Create cycle in linked list
    static void createCycle(Node head, int pos) {

        if (pos == -1)
            return;

        Node cycleNode = null;
        Node temp = head;
        int count = 0;

        while (temp.next != null) {

            if (count == pos) {
                cycleNode = temp;
            }

            temp = temp.next;
            count++;
        }

        temp.next = cycleNode;
    }

    // Detect cycle using Floyd Algorithm
    static boolean cycleDetect(Node head) {

        Node slow = head;
        Node fast = head;

        while (fast != null && fast.next != null) {

            slow = slow.next;
            fast = fast.next.next;

            if (slow == fast) {
                return true;
            }
        }

        return false;
    }

    public static void main(String[] args) {

        Scanner sc = new Scanner(System.in);

        int n = sc.nextInt();

        Node head = null;

        // Input linked list
        for (int i = 0; i < n; i++) {
            int val = sc.nextInt();
            head = insertNode(head, val);
        }

        // Position where cycle should start
        int pos = sc.nextInt();

        createCycle(head, pos);

        if (cycleDetect(head)) {
            System.out.println("Cycle Detected");
        } else {
            System.out.println("Cycle Not Detected");
        }

        sc.close();
    }
}